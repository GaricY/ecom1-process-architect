"""Orchestrator CLI: drive the BitGN ECOM benchmark via Claude CLI + MCP.

Usage:
    python -m orchestrator.main                # every task in the benchmark
    python -m orchestrator.main t01            # one task (substring match)
    python -m orchestrator.main t01 t05        # subset
    python -m orchestrator.main --limit 5      # stop after N tasks
    python -m orchestrator.main --no-submit    # leave run open after trials
"""

from __future__ import annotations

import argparse
import asyncio
import atexit
import contextlib
import json
import re
import shutil
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO

from bitgn.vm.ecom.ecom_pb2 import AnswerRequest, Outcome

from . import harness, instructions, session_registry
from .bootstrap import make_vm
from .claude_runner import (
    ClaudeRunResult,
    default_prompt,
    read_answer_file,
    run_claude_cli,
)
from .config import Config, load_config
from .executor_log import write_executor_actions
from .instructions.pa_workdir import PaWorkerConfig, make_pa_worker
from .report import (
    collect_pa_metrics,
    write_pa_aggregate_report,
    write_report,
    write_summary,
)
from .task_dir import PreparedTaskDir, materialize

ERR_INTERNAL_OUTCOME = "OUTCOME_ERR_INTERNAL"


_ACTUAL_TASK_KEYS = ("score_actual", "score_detail_actual")
_ACTUAL_SUMMARY_KEYS = ("hints_by_task_actual",)


def _strip_actuals(summary_dict: dict[str, Any]) -> dict[str, Any]:
    """Return a deep-copied summary with `*_actual` mirrors removed.

    The agent stack sees only this shape — under blind emulation, leaking
    `score_actual` / `hints_by_task_actual` into `summary.json` would defeat
    the point of emulation. Outside emulation this is a harmless no-op
    cleanup (the fields equal the visible ones anyway).
    """
    rebuilt = json.loads(json.dumps(summary_dict))
    for key in _ACTUAL_SUMMARY_KEYS:
        rebuilt.pop(key, None)
    for task in rebuilt.get("tasks") or []:
        for key in _ACTUAL_TASK_KEYS:
            task.pop(key, None)
    return rebuilt


def _actualize_summary(summary_dict: dict[str, Any]) -> dict[str, Any]:
    """Return a deep-copied summary with grader truth restored.

    Under blind emulation `score` / `score_detail` / `hints_by_task` in the
    main summary are masked to keep the agent stack truly blind. The sibling
    `<run_id>-score/` report needs the real values; this helper rebuilds a
    dict where each task's `score` / `score_detail` come from its
    `*_actual` mirror and `hints_by_task` comes from `hints_by_task_actual`.
    The `*_actual` fields are stripped from the result so the `-score` dump
    matches the prod blind shape but with truth substituted in.
    """
    rebuilt = json.loads(json.dumps(summary_dict))
    rebuilt["hints_by_task"] = dict(summary_dict.get("hints_by_task_actual") or {})
    for task in rebuilt.get("tasks") or []:
        if "score_actual" in task:
            task["score"] = task.get("score_actual")
        if "score_detail_actual" in task:
            task["score_detail"] = list(task.get("score_detail_actual") or [])
    for key in _ACTUAL_SUMMARY_KEYS:
        rebuilt.pop(key, None)
    for task in rebuilt.get("tasks") or []:
        for key in _ACTUAL_TASK_KEYS:
            task.pop(key, None)
    return rebuilt


class _ConsoleTee:
    def __init__(self, primary: TextIO, log: TextIO) -> None:
        self._primary = primary
        self._log = log
        self.encoding = getattr(primary, "encoding", "utf-8")
        self.errors = getattr(primary, "errors", "replace")

    def write(self, data: str) -> int:
        self._primary.write(data)
        # During interpreter shutdown the atexit-registered _close_log has
        # already closed the log handle by the time flush_std_files() reaches
        # us — skip silently rather than letting the shutdown flusher trip.
        if not self._log.closed:
            self._log.write(data)
        return len(data)

    def flush(self) -> None:
        self._primary.flush()
        if not self._log.closed:
            self._log.flush()

    def isatty(self) -> bool:
        return self._primary.isatty()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._primary, name)


def _install_console_log(console_log_path: Path) -> None:
    console_log_path.parent.mkdir(parents=True, exist_ok=True)
    log_fh = console_log_path.open("a", encoding="utf-8", buffering=1)
    sys.stdout = _ConsoleTee(sys.stdout, log_fh)  # type: ignore[assignment]
    sys.stderr = _ConsoleTee(sys.stderr, log_fh)  # type: ignore[assignment]

    def _close_log() -> None:
        with contextlib.suppress(Exception):
            log_fh.flush()
        with contextlib.suppress(Exception):
            log_fh.close()

    atexit.register(_close_log)


@dataclass
class ScoreEntry:
    task_id: str
    trial_id: str
    task_dir: str
    answer_outcome: str
    # `score` / `score_detail` are what the agent stack (Executor log, PA,
    # report.md, summary.json) actually see. Under blind emulation they are
    # forced to None / [] regardless of what the grader returned.
    score: float | None
    score_detail: list[str]
    # `*_actual` mirror what the grader really returned. Outside blind
    # emulation they equal `score` / `score_detail`; under emulation they
    # are the only place the truth survives (used to build the sibling
    # `<run_id>-score/` report for human review).
    score_actual: float | None
    score_detail_actual: list[str]
    status: str
    num_turns: int | None
    cost_usd: float | None
    duration_sec: int
    mcp_calls: int
    executor_attempts: int
    internal_error_retries: int
    start_trial_at: float
    end_trial_at: float
    bootstrap_sec: int
    trial_sec: int
    business_process_raw: str | None = None
    business_process: str | None = None
    process_architect_dir: str | None = None
    process_architect_terminal_status: str | None = None
    process_architect_created_versions: list[dict[str, str]] = field(default_factory=list)
    instruction_selection_status: str | None = None
    instruction_units: list[dict[str, str | None]] = field(default_factory=list)


@dataclass
class Summary:
    run_id: str
    # Real BitGN harness run id (e.g. `run-22Rp…`), as returned by `start_run`
    # and shown on the leaderboard. `run_id` above is the local timestamp dir
    # name; this is the id you paste into `eu.bitgn.com/runs/<id>` and feed to
    # the `finalize-run` skill.
    harness_run_id: str
    benchmark: str
    run_name: str
    model: str
    effort: str
    concurrency: int
    pa_llm_concurrency: int
    trial_start_interval_sec: int
    stale_resolution: str
    wall_clock_sec: int = 0
    tasks: list[ScoreEntry] = field(default_factory=list)
    # `hints_by_task` is what the agent stack and report.md see. Under
    # blind emulation it is forced empty (prod blind benchmarks return
    # empty hints anyway). `hints_by_task_actual` keeps the true mapping
    # for the sibling `-score/` report.
    hints_by_task: dict[str, str] = field(default_factory=dict)
    hints_by_task_actual: dict[str, str] = field(default_factory=dict)
    blind_emulation: bool = False


def parse_args(cfg: Config) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="ecom-agent",
        description="Drive BitGN ECOM tasks via Claude CLI + MCP execute_python.",
    )
    p.add_argument("tasks", nargs="*", help="task IDs to run (substring match)")
    p.add_argument("--bitgn-api-key", default=cfg.bitgn_api_key)
    p.add_argument("--host", default=cfg.benchmark_host)
    p.add_argument("--benchmark", default=cfg.benchmark_id)
    p.add_argument("--run-name", default=cfg.run_name)
    p.add_argument("--claude-bin", default=cfg.claude_bin)
    p.add_argument("--model", default=cfg.claude_model)
    p.add_argument(
        "--effort",
        default=cfg.claude_reasoning_effort,
        choices=["low", "medium", "high", "xhigh", "max"],
    )
    p.add_argument("--max-turns", type=int, default=cfg.claude_max_turns)
    p.add_argument("--concurrency", type=int, default=cfg.concurrency)
    p.add_argument(
        "--pa-llm-concurrency", type=int, default=cfg.pa_llm_concurrency,
        help=(
            "Concurrent Process Architect LLM jobs allowed in flight. "
            "Independent of --concurrency: Executor and PA call different "
            "models and hit separate rate limits. Set to 0 to disable PA "
            "entirely (no failure_fix, no refresh, no world_refresh — no "
            "PA workdirs materialised, no tokens burned)."
        ),
    )
    p.add_argument(
        "--world-refresh",
        dest="world_refresh_enabled",
        action="store_true",
        default=cfg.world_refresh_enabled,
        help=(
            "Enable the world_refresh PA mode. Independent of PA itself: "
            "when off (default), world-layer drift is still surfaced to the "
            "Executor but no world_refresh PA job is materialised, and "
            "failure_fix / refresh keep running normally. Requires PA "
            "enabled (--pa-llm-concurrency > 0)."
        ),
    )
    p.add_argument(
        "--no-world-refresh",
        dest="world_refresh_enabled",
        action="store_false",
        help="Disable the world_refresh PA mode (default).",
    )
    p.add_argument(
        "--world-create",
        dest="world_create_enabled",
        action="store_true",
        default=cfg.world_create_enabled,
        help=(
            "Use `world_create` (not `world_refresh`) for the world-PA "
            "pathway. Operator opt-in for two cases: (a) baseline is empty "
            "(seed v0001 from current dump) — resolver forces a one-off "
            "create at the first trial; (b) the world has drifted so far "
            "from baseline that an incremental refresh is the wrong shape. "
            "Sets the PA prompt to world_create.md; workdir layout matches "
            "world_refresh (drifts may be empty when no baseline exists)."
        ),
    )
    p.add_argument(
        "--no-world-create",
        dest="world_create_enabled",
        action="store_false",
        help="Use world_refresh for the world-PA pathway (default).",
    )
    p.add_argument(
        "--pa-apply",
        dest="pa_apply",
        action="store_true",
        default=cfg.pa_apply,
        help=(
            "Apply validated PA decisions (write new vNNNN, advance baseline). "
            "Default: enabled. Pass --no-pa-apply for dry-run mode: PA still "
            "writes pa-output/ and the validator runs, but no vNNNN is created "
            "and the job's terminal_status becomes `dry_run_completed`. Useful "
            "for prompt-debugging without polluting the instruction store."
        ),
    )
    p.add_argument(
        "--no-pa-apply",
        dest="pa_apply",
        action="store_false",
        help="Dry-run mode: validate PA output, skip apply, write dry-run-summary.md.",
    )
    p.add_argument(
        "--pa-fix",
        dest="pa_fix_enabled",
        action="store_true",
        default=cfg.pa_fix_enabled,
        help=(
            "Allow PA `fix` and `fix_blind` jobs after trial failures. "
            "Default: disabled. Pass --pa-fix to enable both modes (refresh / "
            "world_refresh / world_create are gated separately). PA picks "
            "fix_blind when score is unavailable (blind eval) and fix otherwise."
        ),
    )
    p.add_argument(
        "--no-pa-fix",
        dest="pa_fix_enabled",
        action="store_false",
        help="Skip both PA fix and fix_blind modes for this run.",
    )
    p.add_argument(
        "--refresh",
        dest="refresh_enabled",
        action="store_true",
        default=cfg.refresh_enabled,
        help=(
            "Enable the per-unit `refresh` PA mode. Independent of PA "
            "itself and of world_refresh: when off (default), per-unit "
            "dependency drift is still surfaced to the Executor (stale "
            "fallback is rendered) but no refresh PA job is enqueued, and "
            "failure_fix / world_refresh keep running normally. Requires "
            "PA enabled (--pa-llm-concurrency > 0)."
        ),
    )
    p.add_argument(
        "--no-refresh",
        dest="refresh_enabled",
        action="store_false",
        help="Disable the per-unit refresh PA mode (default).",
    )
    p.add_argument(
        "--stale-resolution",
        default=cfg.stale_resolution,
        choices=["latest_async_refresh", "wait_for_refresh"],
        help=(
            "When an instruction unit's dependencies do not match the live "
            "task dump, either render the latest fallback and queue a PA "
            "refresh in the background (latest_async_refresh) or wait for "
            "PA to produce a matching version before starting the Executor "
            "(wait_for_refresh)."
        ),
    )
    p.add_argument(
        "--trial-start-interval",
        type=int,
        default=cfg.trial_start_interval_sec,
        help=(
            "Minimum seconds between successive start_trial RPCs. "
            "Spacing happens before start_trial so the organiser's "
            "trial-time counter only includes our actual work. 0 disables."
        ),
    )
    p.add_argument("--runs-root", default=cfg.runs_root)
    p.add_argument("--limit", type=int, default=None)
    submit_group = p.add_mutually_exclusive_group()
    submit_group.add_argument(
        "--submit",
        dest="submit",
        action="store_true",
        default=True,
        help="Submit the run after all selected trials finish (default).",
    )
    submit_group.add_argument(
        "--no-submit",
        dest="submit",
        action="store_false",
        help="Leave the run open after trials finish.",
    )
    p.add_argument(
        "--snippet-timeout",
        type=int,
        default=180,
        help="per-snippet wall-clock timeout (seconds)",
    )
    p.add_argument(
        "--trial-timeout",
        type=int,
        default=1800,
        help="per-trial wall-clock timeout (seconds) for the Claude CLI",
    )
    p.add_argument(
        "--internal-error-retries",
        type=int,
        default=5,
        help=(
            "Retry Executor this many times before submitting fallback "
            "OUTCOME_ERR_INTERNAL. Retries happen before endTrial."
        ),
    )
    p.add_argument(
        "--process-architect",
        dest="process_architect",
        action="store_true",
        default=True,
        help="On FAIL, spawn the Process Architect to edit business_processes/.",
    )
    p.add_argument(
        "--no-process-architect",
        dest="process_architect",
        action="store_false",
        help="Disable the Process Architect even on FAIL.",
    )
    p.add_argument(
        "--process-architect-model",
        default=cfg.pa_claude_model,
        help="Claude model used by the Process Architect.",
    )
    p.add_argument(
        "--process-architect-effort",
        default=cfg.pa_claude_reasoning_effort,
        choices=["low", "medium", "high", "xhigh", "max"],
        help="Reasoning effort used by the Process Architect.",
    )
    p.add_argument(
        "--process-architect-timeout",
        type=int,
        default=cfg.process_architect_timeout_sec,
        help=(
            "Wall-clock timeout for one Process Architect run in non-world "
            "modes (refresh / failure_fix / fix_blind / conflict retry), "
            "seconds. Default 1200."
        ),
    )
    p.add_argument(
        "--process-architect-world-timeout",
        type=int,
        default=cfg.process_architect_world_timeout_sec,
        help=(
            "Wall-clock timeout for one Process Architect run in world_refresh "
            "/ world_create modes, seconds. These passes can touch every BP on "
            "heavy upstream drift, so they get a separate budget. Default 7200 "
            "(2h)."
        ),
    )
    p.add_argument(
        "--process-architect-max-turns",
        type=int,
        default=cfg.pa_max_turns,
        help=(
            "Max Claude turns per Process Architect attempt. Independent of "
            "--max-turns (which caps the Executor): PA workdirs can span many "
            "BPs on heavy world drift and the executor cap (40 by default) is "
            "far too low. Default 0 = unlimited (omit --max-turns when spawning "
            "claude); PA is gated by --process-architect-timeout instead."
        ),
    )
    p.add_argument(
        "--wait-process-architect",
        action="store_true",
        help=(
            "Wait for failure-fix PA jobs and include their terminal status "
            "in the per-task summary. By default PA is queued best-effort and "
            "does not delay run submission."
        ),
    )
    p.add_argument(
        "--pa-conflict-mode",
        dest="pa_conflict_mode",
        action="store_true",
        default=cfg.pa_conflict_mode,
        help=(
            "Enable post-LLM stale-base detection. If `base_version` is no "
            "longer latest at apply time (a concurrent PA published a newer "
            "version), spawn a second LLM pass with conflict.md and rebase "
            "the patch. Default: enabled."
        ),
    )
    p.add_argument(
        "--no-pa-conflict-mode",
        dest="pa_conflict_mode",
        action="store_false",
        help="Disable conflict mode (silent forks under parallel PA).",
    )
    p.add_argument(
        "--pa-conflict-max-retries",
        type=int,
        default=cfg.pa_conflict_max_retries,
        help="Max conflict retries per PA job (default 1).",
    )
    p.add_argument(
        "--blind-emulation",
        dest="blind_emulation",
        action="store_true",
        default=cfg.blind_emulation,
        help=(
            "Emulate the prod BLIND evaluation policy: drop score, "
            "score_detail and per-task hints from everything the agent "
            "stack (Executor, PA, summary.json, report.md, "
            "executor_actions.md, result.json) can see. The real values "
            "are still recorded in a sibling `<run_id>-score/` dir as "
            "summary.json + report.md for human review."
        ),
    )
    p.add_argument(
        "--no-blind-emulation",
        dest="blind_emulation",
        action="store_false",
        help="Disable blind emulation (default).",
    )
    p.add_argument(
        "--dump-sql-rows",
        type=int,
        default=cfg.dump_sql_rows,
        help=(
            "If >0, dump up to N rows per user table during bootstrap to "
            "`<task_dir>/dump_sql/<table>.csv` plus a `manifest.json` with "
            "per-table total_rows/dumped_rows/truncated. 0 (default) disables."
        ),
    )
    return p.parse_args()


def iso_stamp(now: datetime | None = None) -> str:
    # Local wall-clock — easier to correlate with logs the user sees in the
    # terminal than UTC.
    return (now or datetime.now()).strftime("%Y%m%d-%H%M%S")


def short_outcome(s: str) -> str:
    return re.sub(r"^OUTCOME_", "", s or "")


def _natural(s: str) -> list[Any]:
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def _resolve_python_bin(project_root: Path) -> Path:
    venv = project_root / ".venv" / "bin" / "python"
    if venv.exists():
        return venv
    candidate = Path("/usr/bin/python3")
    return candidate if candidate.exists() else Path("python3")


def _archive_executor_attempt(task_dir: Path, attempt_no: int) -> None:
    logs_dir = task_dir / ".logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    moves = [
        (
            logs_dir / "transcript.jsonl",
            logs_dir / f"transcript-attempt-{attempt_no:02d}.jsonl",
        ),
        (
            logs_dir / "claude-stderr.log",
            logs_dir / f"claude-stderr-attempt-{attempt_no:02d}.log",
        ),
        (
            task_dir / "answer.json",
            logs_dir / f"answer-attempt-{attempt_no:02d}.json",
        ),
        (
            task_dir / "result.json",
            logs_dir / f"claude-result-attempt-{attempt_no:02d}.jsonl",
        ),
    ]
    for src, dst in moves:
        if not src.exists():
            continue
        if dst.exists():
            dst.unlink()
        shutil.move(str(src), str(dst))


def _aggregate_run_results(results: list[ClaudeRunResult]) -> ClaudeRunResult:
    if not results:
        return ClaudeRunResult(
            exit_code=1,
            duration_ms=0,
            num_turns=None,
            total_cost_usd=None,
            is_error=True,
            stop_reason=None,
            result_text="Claude CLI did not run.",
            session_id=None,
            mcp_calls=0,
        )
    last = results[-1]
    turns = [r.num_turns for r in results if r.num_turns is not None]
    costs = [r.total_cost_usd for r in results if r.total_cost_usd is not None]
    return ClaudeRunResult(
        exit_code=last.exit_code,
        duration_ms=sum(r.duration_ms for r in results),
        num_turns=sum(turns) if turns else None,
        total_cost_usd=sum(costs) if costs else None,
        is_error=last.is_error,
        stop_reason=last.stop_reason,
        result_text=last.result_text,
        session_id=last.session_id,
        mcp_calls=sum(r.mcp_calls for r in results),
    )


def _retry_reason(answer: Any | None) -> str | None:
    if answer is None:
        return "no answer.json"
    if getattr(answer, "outcome", None) == ERR_INTERNAL_OUTCOME:
        return ERR_INTERNAL_OUTCOME
    return None


def _business_process_from_scratchpad(
    scratchpad_path: Path,
) -> tuple[str | None, str | None]:
    try:
        raw = json.loads(scratchpad_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, None
    if not isinstance(raw, dict):
        return None, None
    value = raw.get("business_process")
    if isinstance(value, dict):
        value = value.get("primary")
    if not isinstance(value, str):
        return None, None
    bp_raw = value.strip()
    if not bp_raw:
        return None, None
    bp_name = bp_raw.rsplit("/", 1)[-1]
    if bp_name.endswith(".md"):
        bp_name = bp_name[:-3]
    return bp_raw, bp_name or None


class TrialStartGate:
    """Spacing gate around `start_trial` RPCs.

    The dispatcher calls `wait()` before each `start_trial`. If the previous
    matched trial was started less than `interval_sec` ago, `wait()` sleeps
    just long enough to honour the interval. Only matched trials should call
    `record()` — filtered trials must NOT advance the gate, otherwise smoke
    runs (filter rejects most trials) become artificially slow.

    `record()` accepts the monotonic timestamp captured *before* the
    `start_trial` RPC, so the next trial's wait is measured from "we hit
    start_trial" rather than "start_trial RPC returned" — keeping spacing
    independent of RPC latency.
    """

    def __init__(self, interval_sec: int) -> None:
        self._interval_sec = max(0, interval_sec)
        self._last_start: float | None = None

    async def wait(self) -> None:
        if self._interval_sec <= 0 or self._last_start is None:
            return
        elapsed = time.monotonic() - self._last_start
        delay = self._interval_sec - elapsed
        if delay > 0:
            await asyncio.sleep(delay)

    def record(self, started_mono: float) -> None:
        self._last_start = started_mono


def _mcp_servers_config(
    *,
    python_bin: Path,
    project_root: Path,
    session_id: str,
    sessions_dir: Path,
) -> dict[str, dict]:
    """Per-trial MCP server config (handed to Claude CLI via --mcp-config)."""
    return {
        "ecom-python": {
            "command": str(python_bin),
            "args": ["-m", "orchestrator.mcp_python_server"],
            "env": {
                "PYTHONPATH": str(project_root),
                session_registry.ENV_SESSION_ID: session_id,
                session_registry.ENV_SESSIONS_DIR: str(sessions_dir),
            },
        }
    }


async def _submit_skip_trial(host: str, plan: harness.TrialPlan) -> None:
    """Close a trial that is not in the requested subset.

    Subset / single-task runs still have to `start_trial` *every* trial to
    learn its `task_id` — the filter is a substring match on `task_id`,
    which the harness only reveals after `start_trial`. Trials that do not
    match must not be left dangling: under the post-submit scoring contract
    `submit_run(force=True)` finalises the whole run, so an un-answered open
    trial would be scored as incomplete and its VM stays provisioned. We
    submit OUTCOME_ERR_INTERNAL and end the trial (mirrors the no-answer
    fallback in `run_one_task`).
    """
    try:
        await asyncio.to_thread(
            lambda: make_vm(plan.harness_url).answer(
                AnswerRequest(
                    message="Task not in requested subset; skipped.",
                    outcome=Outcome.OUTCOME_ERR_INTERNAL,
                    refs=[],
                )
            )
        )
    except Exception as exc:
        print(f"[skip {plan.task_id}] answer error: {exc}")
    try:
        await asyncio.to_thread(harness.end_trial, host, plan.trial_id)
    except Exception as exc:
        print(f"[skip {plan.task_id}] end_trial error: {exc}")


async def run_one_task(
    *,
    plan: harness.TrialPlan,
    idx: int,
    total: int,
    start_trial_at: float,
    benchmark_id: str,
    run_dir: Path,
    sessions_dir: Path,
    static_dir: Path,
    opts: argparse.Namespace,
    project_root: Path,
    python_bin: Path,
    pa_queue: instructions.PaQueue,
    blind_eval: bool,
) -> ScoreEntry:
    label = f"[{idx + 1}/{total} {plan.task_id}]"
    task_dir = run_dir / f"{idx + 1:04d}-{plan.task_id}-{plan.trial_id}"
    print(f"--- {label} ---")
    print(
        f"{label} trial={plan.trial_id} dir={task_dir}\n"
        f"{label} instruction: "
        f"{plan.instruction[:200]}{'…' if len(plan.instruction) > 200 else ''}"
    )

    bootstrap_started_at = time.time()

    # 1. Materialise the task dir (pre-bootstrap + bin-help).
    prepared: PreparedTaskDir = await asyncio.to_thread(
        materialize,
        harness_url=plan.harness_url,
        task_dir=task_dir,
        static_instructions_dir=static_dir,
        benchmark_id=benchmark_id,
        task_id=plan.task_id,
        trial_id=plan.trial_id,
        instruction=plan.instruction,
        dump_sql_rows=opts.dump_sql_rows,
        world_modes_enabled=opts.world_create_enabled or opts.world_refresh_enabled,
    )

    print(
        f"{label} pre-bootstrap: {prepared.pre_bootstrap.files_copied} files; "
        f"bin-help={prepared.bin_help.bin_help_hash[:12]}… "
        f"tools={len(prepared.bin_help.tools)}"
    )
    if prepared.dump_sql is not None:
        print(
            f"{label} dump_sql: tables={len(prepared.dump_sql.tables_dumped)} "
            f"limit={opts.dump_sql_rows} "
            f"errors={len(prepared.dump_sql.errors)}"
        )

    # 1b. Resolve + render versioned instruction units into the task dir.
    selection = await instructions.resolve_and_render(
        project_root=project_root,
        task_dir=prepared.task_dir,
        task_id=plan.task_id,
        trial_id=plan.trial_id,
        stale_resolution=opts.stale_resolution,
        pa_queue=pa_queue,
        substitutions={
            "TRIAL_IDENTITY": prepared.trial_prerender.identity,
            "TRIAL_DATE": prepared.trial_prerender.date,
        },
        label=label,
    )
    instruction_units_summary = [
        {
            "unit_id": u.unit_id,
            "selected_version": u.selected_version,
            "selection_status": u.selection_status,
        }
        for u in selection.units
    ]
    bootstrap_finished_at = time.time()

    # 2. Register session id with harness URL (outside the task dir).
    session_id = session_registry.new_session_id()
    session_registry.register(
        run_root=run_dir,
        session_id=session_id,
        payload={
            "harness_url": plan.harness_url,
            "task_dir": str(prepared.task_dir),
            "python_dir": str(prepared.python_dir),
            "answer_path": str(prepared.answer_path),
            "scratchpad_path": str(prepared.scratchpad_path),
            "state_path": str(prepared.state_path),
            "tool_calls_path": str(prepared.tool_calls_path),
            "runtime_prelude_path": str(prepared.runtime_prelude_path),
            "python_bin": str(python_bin),
            "snippet_timeout_sec": opts.snippet_timeout,
            "benchmark_id": benchmark_id,
            "task_id": plan.task_id,
            "trial_id": plan.trial_id,
        },
    )

    sessions_root = session_registry.sessions_dir(run_dir)
    mcp_servers = _mcp_servers_config(
        python_bin=python_bin,
        project_root=project_root,
        session_id=session_id,
        sessions_dir=sessions_root,
    )

    env_for_claude: dict[str, str] = {
        # Anthropic CLI auth is read from the parent process's env / ~/.claude;
        # we do NOT inject BITGN_API_KEY or harness_url here.
        "PYTHONPATH": str(project_root),
    }

    task_status = "completed"
    attempt_results: list[ClaudeRunResult] = []
    answer = None
    max_retries = max(0, int(getattr(opts, "internal_error_retries", 0) or 0))
    max_attempts = max_retries + 1
    try:
        for attempt_no in range(1, max_attempts + 1):
            if attempt_no > 1:
                _archive_executor_attempt(prepared.task_dir, attempt_no - 1)
                retry_delay = 10 * (attempt_no - 1)
                print(
                    f"{label} retrying Executor after internal error "
                    f"(attempt {attempt_no}/{max_attempts}) after "
                    f"{retry_delay}s backoff"
                )
                await asyncio.sleep(retry_delay)
            else:
                print(f"{label} Executor attempt {attempt_no}/{max_attempts}")

            try:
                attempt_result = await run_claude_cli(
                    claude_bin=opts.claude_bin,
                    task_dir=prepared.task_dir,
                    prompt=default_prompt(),
                    max_turns=opts.max_turns,
                    effort=opts.effort,
                    model=opts.model,
                    env=env_for_claude,
                    answer_path=prepared.answer_path,
                    answer_grace_sec=15.0,
                    overall_timeout_sec=float(opts.trial_timeout),
                    label=label,
                    scrub_secrets=[plan.harness_url],
                    mcp_servers=mcp_servers,
                )
            except Exception as exc:
                print(f"{label} claude CLI invocation failed: {exc}")
                attempt_result = ClaudeRunResult(
                    exit_code=1,
                    duration_ms=0,
                    num_turns=None,
                    total_cost_usd=None,
                    is_error=True,
                    stop_reason=None,
                    result_text=str(exc),
                    session_id=None,
                    mcp_calls=0,
                )
            attempt_results.append(attempt_result)
            answer = read_answer_file(prepared.answer_path)
            reason = _retry_reason(answer)
            if reason is None:
                break
            task_status = "error"
            print(
                f"{label} Executor attempt {attempt_no}/{max_attempts} "
                f"ended with {reason}"
            )
            if attempt_no >= max_attempts:
                break
    finally:
        session_registry.clear(run_root=run_dir, session_id=session_id)

    run_result = _aggregate_run_results(attempt_results)
    if answer is None:
        task_status = "error"
        print(f"{label} no answer.json produced — submitting fallback ERR_INTERNAL")
        try:
            make_vm(plan.harness_url).answer(
                AnswerRequest(
                    message="Agent did not produce an answer.",
                    outcome=Outcome.OUTCOME_ERR_INTERNAL,
                    refs=[],
                )
            )
        except Exception as exc:
            print(f"{label} fallback submit error: {exc}")
        answer_outcome = ERR_INTERNAL_OUTCOME
    else:
        answer_outcome = answer.outcome
        print(f"{label} answer: outcome={answer_outcome} refs={len(answer.refs)}")
        if answer_outcome == ERR_INTERNAL_OUTCOME:
            task_status = "error"
    business_process_raw, business_process = _business_process_from_scratchpad(
        prepared.scratchpad_path
    )

    # Scores are no longer surfaced by `end_trial`; they arrive only after
    # `submit_run` and are backfilled into ScoreEntry in `amain`. We still
    # call `end_trial` for its side effect (closes the server-side slot).
    try:
        await asyncio.to_thread(harness.end_trial, opts.host, plan.trial_id)
    except Exception as exc:
        print(f"{label} endTrial error: {exc}")
    end_trial_at = time.time()

    score: float | None = None
    score_detail: list[str] = []
    score_actual: float | None = None
    score_detail_actual: list[str] = []

    bootstrap_sec = int(bootstrap_finished_at - bootstrap_started_at)
    trial_sec = int(end_trial_at - start_trial_at)

    # Persist per-trial result.json next to artifacts. `score_pending`
    # marks the (now-default) case where the verdict has not yet been
    # revealed by the harness — backfill happens in amain after submit_run.
    result_json = {
        "task_id": plan.task_id,
        "trial_id": plan.trial_id,
        "answer_outcome": answer_outcome,
        "score": score,
        "score_detail": score_detail,
        "score_pending": True,
        "num_turns": run_result.num_turns,
        "cost_usd": run_result.total_cost_usd,
        "duration_sec": run_result.duration_ms // 1000,
        "mcp_calls": run_result.mcp_calls,
        "executor_attempts": len(attempt_results),
        "internal_error_retries": max(0, len(attempt_results) - 1),
        "business_process_raw": business_process_raw,
        "business_process": business_process,
        "start_trial_at": start_trial_at,
        "bootstrap_started_at": bootstrap_started_at,
        "bootstrap_finished_at": bootstrap_finished_at,
        "end_trial_at": end_trial_at,
        "bootstrap_sec": bootstrap_sec,
        "trial_sec": trial_sec,
        "claude_session_id": run_result.session_id,
        "claude_stop_reason": run_result.stop_reason,
    }
    (task_dir / "result.json").write_text(
        json.dumps(result_json, indent=2), encoding="utf-8"
    )

    print(
        f"{label} done: score=pending {short_outcome(answer_outcome)} "
        f"turns={run_result.num_turns or '?'} mcp={run_result.mcp_calls} "
        f"{run_result.duration_ms // 1000}s "
        f"boot={bootstrap_sec}s trial={trial_sec}s"
    )

    # Build the human/agent-readable executor log every trial; it doubles
    # as the Process Architect's primary reading material on FAIL.
    try:
        executor_log_path = write_executor_actions(
            task_dir=task_dir,
            task_id=plan.task_id,
            trial_id=plan.trial_id,
            instruction=plan.instruction,
            score=score,
            score_detail=score_detail,
            answer_outcome=answer_outcome,
        )
        print(f"{label} executor log: {executor_log_path.name}")
    except Exception as exc:
        print(f"{label} warn: executor_log writer failed: {exc}")

    pa_dir_str: str | None = None
    pa_terminal_status: str | None = None
    pa_created_versions: list[dict[str, str]] = []
    # In-trial PA dispatch is now limited to `fix_blind`. Under blind eval
    # the grader will never reveal a score, so PA must work from the
    # Executor trace alone, and there's no reason to defer to post-submit.
    # Open-eval `failure_fix` is dispatched in amain after submit_run +
    # get_run reveal the per-trial verdicts.
    pa_fix_eligible = (
        blind_eval
        and getattr(opts, "process_architect", True)
        and getattr(opts, "pa_fix_enabled", True)
        and not pa_queue.disabled
        and answer_outcome != ERR_INTERNAL_OUTCOME
    )
    if pa_fix_eligible and pa_queue.world_refresh_seen:
        print(
            f"{label} PA fix_blind skipped: world_refresh ran in this "
            "run, stale world makes per-unit PA pointless"
        )
        pa_terminal_status = "skipped_world_refresh"
        pa_fix_eligible = False
    if pa_fix_eligible:
        print(f"{label} queueing Process Architect fix_blind")
        if getattr(opts, "wait_process_architect", False):
            pa_result = await instructions.run_failure_fix(
                project_root=project_root,
                failed_task_dir=task_dir,
                task_id=plan.task_id,
                trial_id=plan.trial_id,
                instruction=plan.instruction,
                score=score,
                score_detail=score_detail,
                answer_outcome=answer_outcome,
                pa_queue=pa_queue,
                label=label,
                mode="fix_blind",
            )
            pa_dir_str = pa_result.pa_dir
            pa_terminal_status = pa_result.terminal_status
            pa_created_versions = pa_result.created_versions
            if pa_result.error:
                print(f"{label} [PA] error: {pa_result.error}")
            print(
                f"{label} [PA] done: status={pa_result.terminal_status} "
                f"duration={pa_result.duration_ms // 1000}s "
                f"created={pa_result.created_versions or '[]'}"
            )
        else:
            pa_future, pa_dir, _ = instructions.queue_failure_fix(
                project_root=project_root,
                failed_task_dir=task_dir,
                task_id=plan.task_id,
                trial_id=plan.trial_id,
                instruction=plan.instruction,
                score=score,
                score_detail=score_detail,
                answer_outcome=answer_outcome,
                pa_queue=pa_queue,
                label=label,
                mode="fix_blind",
            )
            pa_dir_str = str(pa_dir)
            pa_terminal_status = "queued"

            def _log_pa_done(fut: asyncio.Future[instructions.PaJobResult]) -> None:
                if fut.cancelled():
                    print(f"{label} [PA] cancelled before completion")
                    return
                try:
                    res = fut.result()
                except Exception as exc:
                    print(f"{label} [PA] failed outside trial path: {exc!r}")
                    return
                if res.error:
                    print(f"{label} [PA] error: {res.error}")
                print(
                    f"{label} [PA] done: status={res.terminal_status} "
                    f"duration={res.duration_ms // 1000}s "
                    f"created={res.created_versions or '[]'}"
                )

            pa_future.add_done_callback(_log_pa_done)

    return ScoreEntry(
        task_id=plan.task_id,
        trial_id=plan.trial_id,
        task_dir=str(task_dir),
        answer_outcome=answer_outcome,
        score=score,
        score_detail=score_detail,
        score_actual=score_actual,
        score_detail_actual=score_detail_actual,
        status=task_status,
        num_turns=run_result.num_turns,
        cost_usd=run_result.total_cost_usd,
        duration_sec=run_result.duration_ms // 1000,
        mcp_calls=run_result.mcp_calls,
        executor_attempts=len(attempt_results),
        internal_error_retries=max(0, len(attempt_results) - 1),
        start_trial_at=start_trial_at,
        end_trial_at=end_trial_at,
        bootstrap_sec=bootstrap_sec,
        trial_sec=trial_sec,
        business_process_raw=business_process_raw,
        business_process=business_process,
        process_architect_dir=pa_dir_str,
        process_architect_terminal_status=pa_terminal_status,
        process_architect_created_versions=pa_created_versions,
        instruction_selection_status=selection.status,
        instruction_units=instruction_units_summary,
    )


async def amain() -> int:
    cfg = load_config()
    opts = parse_args(cfg)

    project_root = Path(__file__).resolve().parent.parent
    static_dir = project_root / "static-instructions"
    if not static_dir.is_dir():
        print(f"ERROR: static-instructions/ missing at {static_dir}", file=sys.stderr)
        return 2

    try:
        instructions.preflight_instruction_store(project_root)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    runs_root = Path(opts.runs_root)
    if not runs_root.is_absolute():
        runs_root = (project_root / runs_root).resolve()
    run_id = iso_stamp()
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    _install_console_log(run_dir / "console.log")

    python_bin = _resolve_python_bin(project_root)

    # Sanity-check Claude bin upfront so we fail fast.
    claude_bin = opts.claude_bin
    if not shutil.which(claude_bin):
        print(
            f"warn: claude binary {claude_bin!r} not found on PATH — Claude CLI "
            "calls will fail.",
            file=sys.stderr,
        )

    print(f"Run name:               {opts.run_name}")
    print(f"Run dir:                {run_dir}")
    print(f"Benchmark:              {opts.benchmark}")
    print(f"Host:                   {opts.host}")
    print(f"Claude bin:             {claude_bin}")
    print(f"Claude model:           {opts.model}")
    print(f"Claude reasoning effort:{opts.effort}")
    print(f"Claude max turns:       {opts.max_turns}")
    print(
        f"PA max turns:           "
        f"{opts.process_architect_max_turns if opts.process_architect_max_turns > 0 else 'unlimited'}"
    )
    print(f"PA timeout (non-world): {opts.process_architect_timeout}s")
    print(f"PA timeout (world):     {opts.process_architect_world_timeout}s")
    print(f"Concurrency:            {opts.concurrency}")
    print(
        f"PA LLM concurrency:     {opts.pa_llm_concurrency}"
        f"{' (PA disabled)' if opts.pa_llm_concurrency == 0 else ''}"
    )
    print(
        f"World refresh:          "
        f"{'enabled' if opts.world_refresh_enabled else 'disabled'}"
        f"{' (PA disabled — moot)' if opts.pa_llm_concurrency == 0 else ''}"
    )
    print(
        f"World create:           "
        f"{'enabled' if opts.world_create_enabled else 'disabled'}"
        f"{' (selects world_create over world_refresh mode)' if opts.world_create_enabled else ''}"
    )
    print(
        f"PA apply:               "
        f"{'enabled' if opts.pa_apply else 'dry-run (no vNNNN written)'}"
    )
    print(
        f"PA fix (fix+fix_blind): "
        f"{'enabled' if opts.pa_fix_enabled else 'disabled'}"
    )
    print(
        f"Per-unit refresh:       "
        f"{'enabled' if opts.refresh_enabled else 'disabled'}"
        f"{' (PA disabled — moot)' if opts.pa_llm_concurrency == 0 else ''}"
    )
    print(f"Stale resolution:       {opts.stale_resolution}")
    print(
        f"PA conflict mode:       "
        f"{'enabled' if opts.pa_conflict_mode else 'disabled'} "
        f"(max_retries={opts.pa_conflict_max_retries})"
    )
    print(f"Trial start interval:   {opts.trial_start_interval}s")
    print(f"Blind emulation:        {'enabled' if opts.blind_emulation else 'disabled'}")
    print(
        f"Dump SQL rows:          "
        f"{opts.dump_sql_rows if opts.dump_sql_rows > 0 else 'disabled'}"
    )
    print(f"Python bin (snippet):   {python_bin}")
    print()

    try:
        status = harness.status(opts.host)
        print(f"Harness status: {status['status']} ({status['version']})")
    except Exception as exc:
        print(f"ERROR: harness status: {exc}", file=sys.stderr)
        return 2

    try:
        bench = harness.get_benchmark(opts.host, opts.benchmark)
    except Exception as exc:
        print(f"ERROR: get_benchmark: {exc}", file=sys.stderr)
        return 2
    print(f"Benchmark: {bench.benchmark_id} — {len(bench.task_ids)} tasks")
    upstream_mode = "blind" if bench.is_blind else "open"
    blind_eval = bench.is_blind or opts.blind_emulation
    if opts.blind_emulation and not bench.is_blind:
        print(f"Eval mode: blind (emulated; upstream is {upstream_mode})")
    else:
        print(f"Eval mode: {upstream_mode}")
    print()

    print(
        f"Run mode: {opts.run_name}"
        f"{' (with API key)' if opts.bitgn_api_key else ' (anonymous)'}"
        f"{' [will submit]' if opts.submit else ' [no submit]'}"
    )
    try:
        run_id_str, trial_ids = harness.start_run(
            opts.host,
            benchmark_id=opts.benchmark,
            name=opts.run_name,
            api_key=opts.bitgn_api_key or "",
        )
    except Exception as exc:
        print(f"ERROR: start_run: {exc}", file=sys.stderr)
        return 2
    print(f"Run ID: {run_id_str} ({len(trial_ids)} trials)")

    # Persist the harness run id immediately, before any trial runs. summary.json
    # is only written at the end, so a killed run would otherwise leave the real
    # run id only in console.log. `run.json` lets `finalize-run` (and any post-hoc
    # tooling) recover the leaderboard run id even after an abort.
    try:
        (run_dir / "run.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,  # local timestamp dir name
                    "harness_run_id": run_id_str,  # real BitGN run id
                    "benchmark": opts.benchmark,
                    "host": opts.host,
                    "run_name": opts.run_name,
                    "trial_ids": list(trial_ids),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"warn: failed to write run.json: {exc}", file=sys.stderr)

    if opts.limit and opts.limit > 0:
        trial_ids = trial_ids[: opts.limit]
        print(f"Trial ids (after --limit {opts.limit}): {len(trial_ids)}")

    sessions_root = session_registry.sessions_dir(run_dir)

    summary = Summary(
        run_id=run_id,
        harness_run_id=run_id_str,
        benchmark=opts.benchmark,
        run_name=opts.run_name,
        model=opts.model,
        effort=opts.effort,
        concurrency=opts.concurrency,
        pa_llm_concurrency=opts.pa_llm_concurrency,
        trial_start_interval_sec=opts.trial_start_interval,
        stale_resolution=opts.stale_resolution,
        hints_by_task=({} if opts.blind_emulation else dict(bench.hints_by_task)),
        hints_by_task_actual=dict(bench.hints_by_task),
        blind_emulation=opts.blind_emulation,
    )
    trial_start_gate = TrialStartGate(opts.trial_start_interval)

    pa_worker_config = PaWorkerConfig(
        project_root=project_root,
        claude_bin=opts.claude_bin,
        model=opts.process_architect_model,
        effort=opts.process_architect_effort,
        max_turns=opts.process_architect_max_turns,
        timeout_sec=float(opts.process_architect_timeout),
        world_timeout_sec=float(opts.process_architect_world_timeout),
        conflict_mode=opts.pa_conflict_mode,
        conflict_max_retries=opts.pa_conflict_max_retries,
        pa_apply=opts.pa_apply,
    )
    pa_queue = instructions.PaQueue(
        concurrency=opts.pa_llm_concurrency,
        worker=make_pa_worker(pa_worker_config),
        refresh_enabled=opts.refresh_enabled,
        world_refresh_enabled=opts.world_refresh_enabled,
        world_create_enabled=opts.world_create_enabled,
    )
    pa_queue.start()

    wall_start = time.time()

    raw_total = len(trial_ids)

    async def fn(
        plan: harness.TrialPlan,
        idx: int,
        start_trial_at: float,
        sem: asyncio.Semaphore,
    ) -> ScoreEntry:
        try:
            return await run_one_task(
                plan=plan,
                idx=idx,
                total=raw_total,
                start_trial_at=start_trial_at,
                benchmark_id=opts.benchmark,
                run_dir=run_dir,
                sessions_dir=sessions_root,
                static_dir=static_dir,
                opts=opts,
                project_root=project_root,
                python_bin=python_bin,
                pa_queue=pa_queue,
                blind_eval=blind_eval,
            )
        except asyncio.CancelledError:
            # Best-effort close so the trial does not hang open on BitGN.
            with contextlib.suppress(Exception):
                await asyncio.to_thread(
                    harness.end_trial, opts.host, plan.trial_id
                )
            raise
        except Exception as exc:
            print(f"[{idx + 1} {plan.task_id}] worker crashed: {exc!r}")
            end_at = time.time()
            with contextlib.suppress(Exception):
                await asyncio.to_thread(
                    harness.end_trial, opts.host, plan.trial_id
                )
            return ScoreEntry(
                task_id=plan.task_id,
                trial_id=plan.trial_id,
                task_dir=str(
                    run_dir / f"{idx + 1:04d}-{plan.task_id}-{plan.trial_id}"
                ),
                answer_outcome=ERR_INTERNAL_OUTCOME,
                score=None,
                score_detail=[f"worker crashed: {exc!r}"],
                score_actual=None,
                score_detail_actual=[f"worker crashed: {exc!r}"],
                status="error",
                num_turns=None,
                cost_usd=None,
                duration_sec=0,
                mcp_calls=0,
                executor_attempts=0,
                internal_error_retries=0,
                start_trial_at=start_trial_at,
                end_trial_at=end_at,
                bootstrap_sec=0,
                trial_sec=int(end_at - start_trial_at),
            )
        finally:
            sem.release()

    sem = asyncio.Semaphore(max(1, opts.concurrency))
    workers: list[asyncio.Task[ScoreEntry]] = []
    # Trials filtered out by the `opts.tasks` subset are closed in the
    # background (answer OUTCOME_ERR_INTERNAL + end_trial) so they don't stay
    # open when `submit_run(force=True)` finalises the run. Awaited before
    # submit.
    skip_tasks: list[asyncio.Task[None]] = []
    # trial_id -> instruction. Stashed at start_trial time so the
    # post-submit backfill can rebuild executor_actions.md and queue
    # `failure_fix` PA without round-tripping through task.md.
    instructions_by_trial_id: dict[str, str] = {}
    matched_total = 0

    try:
        for trial_id in trial_ids:
            await sem.acquire()
            await trial_start_gate.wait()
            start_mono = time.monotonic()
            start_trial_at = time.time()
            try:
                plan = await asyncio.to_thread(
                    harness.start_trial, opts.host, trial_id
                )
            except Exception as exc:
                print(f"[? {trial_id}] start_trial failed: {exc!r}")
                # start_trial may have mutated server-side before the response
                # was lost; best-effort end_trial so the slot is released.
                with contextlib.suppress(Exception):
                    await asyncio.to_thread(
                        harness.end_trial, opts.host, trial_id
                    )
                sem.release()
                continue
            if opts.tasks and not any(f in plan.task_id for f in opts.tasks):
                print(
                    f"[skip {plan.task_id}] not in requested subset → "
                    f"submitting {ERR_INTERNAL_OUTCOME}"
                )
                skip_tasks.append(
                    asyncio.create_task(_submit_skip_trial(opts.host, plan))
                )
                sem.release()
                continue
            trial_start_gate.record(start_mono)
            idx = matched_total
            matched_total += 1
            instructions_by_trial_id[plan.trial_id] = plan.instruction
            workers.append(
                asyncio.create_task(fn(plan, idx, start_trial_at, sem))
            )

        entries: list[ScoreEntry] = await asyncio.gather(
            *workers, return_exceptions=False
        )
        # Make sure every unselected trial is closed (ERR_INTERNAL) before we
        # submit the run, otherwise submit_run(force=True) would finalise them
        # as incomplete.
        if skip_tasks:
            print(
                f"Closing {len(skip_tasks)} unselected trial(s) as "
                f"{ERR_INTERNAL_OUTCOME} before submit"
            )
            await asyncio.gather(*skip_tasks, return_exceptions=True)
    except BaseException:
        for t in skip_tasks:
            t.cancel()
        await pa_queue.stop()
        raise

    print(f"Trials matched and dispatched: {matched_total}/{raw_total}")

    summary.tasks = sorted(entries, key=lambda e: _natural(e.task_id))
    summary.wall_clock_sec = int(time.time() - wall_start)

    summary_dict = asdict(summary)
    try:
        pa_totals = collect_pa_metrics(summary_dict, run_dir)
        print(
            f"PA metrics: jobs={pa_totals.get('jobs', 0)} "
            f"cost=${float(pa_totals.get('cost_usd') or 0):.3f} "
            f"turns={pa_totals.get('num_turns', 0)} "
            f"cpu={pa_totals.get('duration_sec', 0)}s"
        )
    except Exception as exc:
        print(f"warn: failed to collect PA metrics: {exc}")

    blind_dict = _strip_actuals(summary_dict)
    summary_path = write_summary(blind_dict, run_dir)
    try:
        report_path = write_report(blind_dict, run_dir)
        print(f"Report:       {report_path}")
    except Exception as exc:
        print(f"warn: failed to write report.md: {exc}")
    if opts.blind_emulation:
        try:
            score_dir = run_dir.parent / f"{run_dir.name}-score"
            score_dir.mkdir(parents=True, exist_ok=True)
            actual_dict = _actualize_summary(summary_dict)
            score_summary_path = write_summary(actual_dict, score_dir)
            score_report_path = write_report(actual_dict, score_dir)
            print(
                f"Blind-emulation truth: {score_summary_path} / {score_report_path}"
            )
        except Exception as exc:
            print(f"warn: failed to write -score sibling: {exc}")
    # NOTE: report_PA.md is intentionally written only AFTER `pa_queue.drain()`
    # below. Background PA jobs are still in flight at this point, so an
    # aggregate written here would show `no_result` / stale terminal_status
    # and misleading "conflict retries: 0" for jobs that conflict-retry later.

    verdict: harness.RunVerdict | None = None
    if opts.submit:
        try:
            submitted = await asyncio.to_thread(
                harness.submit_run, opts.host, run_id_str, force=True
            )
            print(f"Run submitted: {submitted}")
        except Exception as exc:
            print(f"ERROR: submit_run: {exc}")
        else:
            try:
                verdict = await asyncio.to_thread(
                    harness.get_run, opts.host, run_id_str
                )
            except Exception as exc:
                print(f"ERROR: get_run: {exc}")
    else:
        print(
            f"Run {run_id_str} left unsubmitted (--no-submit): scores will "
            "not be available and post-submit failure_fix will not run."
        )

    # Post-submit backfill: attach grader scores to ScoreEntry, rewrite
    # per-task `result.json` + `executor_actions.md` with the real verdict,
    # and queue `failure_fix` PA jobs synchronously so the existing
    # `pa_queue.drain()` below catches them.
    if verdict is not None:
        trial_index = {tv.trial_id: tv for tv in verdict.trials}
        failing_trial_ids: list[str] = []
        for entry in summary.tasks:
            tv = trial_index.get(entry.trial_id)
            if (
                tv is None
                or not tv.score_available
                or tv.score is None
            ):
                continue
            if (
                not blind_eval
                and tv.score < 1.0
                and entry.answer_outcome != ERR_INTERNAL_OUTCOME
            ):
                failing_trial_ids.append(entry.trial_id)
        details: dict[str, harness.TrialDetail] = {}
        if failing_trial_ids:
            print(
                f"Fetching score_detail for {len(failing_trial_ids)} failed "
                "trial(s) via get_trial"
            )
            fetched = await asyncio.gather(
                *(
                    asyncio.to_thread(harness.get_trial, opts.host, tid)
                    for tid in failing_trial_ids
                ),
                return_exceptions=True,
            )
            for tid, res in zip(failing_trial_ids, fetched):
                if isinstance(res, BaseException):
                    print(f"warn: get_trial({tid}) failed: {res}")
                    continue
                details[tid] = res

        for entry in summary.tasks:
            tv = trial_index.get(entry.trial_id)
            if tv is None or not tv.score_available or tv.score is None:
                continue
            entry.score_actual = tv.score
            td = details.get(entry.trial_id)
            if td is not None:
                entry.score_detail_actual = list(td.score_detail)
            if not blind_eval:
                entry.score = entry.score_actual
                entry.score_detail = list(entry.score_detail_actual)

            task_dir = Path(entry.task_dir)
            result_path = task_dir / "result.json"
            try:
                data = json.loads(result_path.read_text(encoding="utf-8"))
                data["score"] = entry.score_actual
                data["score_detail"] = list(entry.score_detail_actual)
                data["score_pending"] = False
                result_path.write_text(
                    json.dumps(data, indent=2), encoding="utf-8"
                )
            except Exception as exc:
                print(f"warn: failed to update {result_path}: {exc}")

            try:
                write_executor_actions(
                    task_dir=task_dir,
                    task_id=entry.task_id,
                    trial_id=entry.trial_id,
                    instruction=instructions_by_trial_id.get(
                        entry.trial_id, ""
                    ),
                    score=entry.score,
                    score_detail=entry.score_detail,
                    answer_outcome=entry.answer_outcome,
                )
            except Exception as exc:
                print(
                    f"warn: failed to rewrite executor_actions for "
                    f"{entry.task_id}: {exc}"
                )

        # Queue post-submit failure_fix burst BEFORE pa_queue.drain().
        # `drain()` is one-shot — it only catches jobs already enqueued
        # by the time `queue.join()` starts. Open-eval failures are
        # dispatched here; blind eval already ran fix_blind in-trial.
        pa_dispatch_eligible = (
            not blind_eval
            and getattr(opts, "process_architect", True)
            and getattr(opts, "pa_fix_enabled", True)
            and not pa_queue.disabled
        )
        if pa_dispatch_eligible and pa_queue.world_refresh_seen:
            print(
                "Post-submit failure_fix skipped: world_refresh ran in this "
                "run, stale world makes per-unit PA pointless"
            )
            pa_dispatch_eligible = False
        if pa_dispatch_eligible:
            queued_count = 0
            for entry in summary.tasks:
                if (
                    entry.score_actual is None
                    or entry.score_actual >= 1.0
                    or entry.answer_outcome == ERR_INTERNAL_OUTCOME
                ):
                    continue
                local_label = f"[{entry.task_id}]"
                pa_future, pa_dir, _ = instructions.queue_failure_fix(
                    project_root=project_root,
                    failed_task_dir=Path(entry.task_dir),
                    task_id=entry.task_id,
                    trial_id=entry.trial_id,
                    instruction=instructions_by_trial_id.get(
                        entry.trial_id, ""
                    ),
                    score=entry.score_actual,
                    score_detail=list(entry.score_detail_actual),
                    answer_outcome=entry.answer_outcome,
                    pa_queue=pa_queue,
                    label=local_label,
                    mode="failure_fix",
                )
                entry.process_architect_dir = str(pa_dir)
                entry.process_architect_terminal_status = "queued"
                queued_count += 1

                def _log_pa_done(
                    fut: asyncio.Future[instructions.PaJobResult],
                    _label: str = local_label,
                ) -> None:
                    if fut.cancelled():
                        print(f"{_label} [PA] cancelled before completion")
                        return
                    try:
                        res = fut.result()
                    except Exception as exc:
                        print(f"{_label} [PA] failed outside trial path: {exc!r}")
                        return
                    if res.error:
                        print(f"{_label} [PA] error: {res.error}")
                    print(
                        f"{_label} [PA] done: status={res.terminal_status} "
                        f"duration={res.duration_ms // 1000}s "
                        f"created={res.created_versions or '[]'}"
                    )

                pa_future.add_done_callback(_log_pa_done)
            if queued_count:
                print(
                    f"Queued {queued_count} post-submit failure_fix PA job(s)"
                )

        # Persist backfilled summary before the scoreboard so disk state
        # matches truth even if drain takes a while or the process dies.
        try:
            summary_dict = asdict(summary)
            blind_dict = _strip_actuals(summary_dict)
            write_summary(blind_dict, run_dir)
            write_report(blind_dict, run_dir)
            if opts.blind_emulation:
                score_dir = run_dir.parent / f"{run_dir.name}-score"
                score_dir.mkdir(parents=True, exist_ok=True)
                actual_dict = _actualize_summary(summary_dict)
                write_summary(actual_dict, score_dir)
                write_report(actual_dict, score_dir)
        except Exception as exc:
            print(f"warn: failed to write post-submit summary/report: {exc}")

    print()
    print(f"┌─── Scoreboard ({len(summary.tasks)}/{raw_total}) ───")
    for s in summary.tasks:
        ss = f"{s.score * 100:.1f}%" if s.score is not None else "N/A"
        icon = "✓" if s.score == 1 else "✗" if s.score == 0 else "·"
        print(
            f"│ {icon} {s.task_id}: {ss} {short_outcome(s.answer_outcome)} "
            f"(turns={s.num_turns or '?'}, mcp={s.mcp_calls}, "
            f"{s.duration_sec}s)"
        )
    valid = [s.score for s in summary.tasks if s.score is not None]
    if valid:
        avg = sum(valid) / len(valid)
        print(f"│ avg: {avg * 100:.1f}% ({len(valid)} scored)")
    total_cpu = sum(s.duration_sec for s in summary.tasks)
    total_trial = sum(s.trial_sec for s in summary.tasks)
    total_boot = sum(s.bootstrap_sec for s in summary.tasks)
    print(
        f"│ wall-clock: {summary.wall_clock_sec}s  cpu-sum: {total_cpu}s  "
        f"trial-sum: {total_trial}s  boot-sum: {total_boot}s  "
        f"concurrency: {opts.concurrency}"
    )
    print("└─────────────────────────")
    print()
    print(f"Summary JSON: {summary_path}")

    print(
        "Run submission path is complete; draining PA queue after submit "
        "for future instruction updates."
    )
    try:
        await pa_queue.drain()
        summary_dict = asdict(summary)
        pa_totals = collect_pa_metrics(summary_dict, run_dir)
        blind_dict = _strip_actuals(summary_dict)
        write_summary(blind_dict, run_dir)
        try:
            report_path = write_report(blind_dict, run_dir)
            print(f"Updated report after PA: {report_path}")
        except Exception as exc:
            print(f"warn: failed to update report.md after PA: {exc}")
        if opts.blind_emulation:
            try:
                score_dir = run_dir.parent / f"{run_dir.name}-score"
                score_dir.mkdir(parents=True, exist_ok=True)
                actual_dict = _actualize_summary(summary_dict)
                write_summary(actual_dict, score_dir)
                score_report_path = write_report(actual_dict, score_dir)
                print(
                    f"Updated blind-emulation truth report: {score_report_path}"
                )
            except Exception as exc:
                print(f"warn: failed to update -score sibling after PA: {exc}")
        try:
            pa_report_path = write_pa_aggregate_report(blind_dict, run_dir)
            print(f"Updated PA report after PA: {pa_report_path}")
        except Exception as exc:
            print(f"warn: failed to update report_PA.md after PA: {exc}")
        print(
            f"PA final metrics: jobs={pa_totals.get('jobs', 0)} "
            f"cost=${float(pa_totals.get('cost_usd') or 0):.3f} "
            f"turns={pa_totals.get('num_turns', 0)} "
            f"cpu={pa_totals.get('duration_sec', 0)}s"
        )
    except Exception as exc:
        print(f"warn: PA drain after submit failed: {exc}")
    finally:
        await pa_queue.stop()
    return 0


def main() -> int:
    try:
        return asyncio.run(amain())
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
