"""Render summary.json / report.md for a finished run."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


def _short_outcome(s: str) -> str:
    return re.sub(r"^OUTCOME_", "", s or "")


def _fmt_score(score) -> str:
    if score is None:
        return "N/A"
    return f"{score * 100:.0f}%"


def _fmt_hms(seconds) -> str:
    try:
        n = int(seconds or 0)
    except (TypeError, ValueError):
        n = 0
    if n < 0:
        n = 0
    h, rem = divmod(n, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}"


def _fmt_cost(cost) -> str:
    if cost is None:
        return "—"
    return f"${cost:.3f}"


def _icon(score) -> str:
    if score is None:
        return "·"
    if score == 1:
        return "✓"
    if score == 0:
        return "✗"
    return "·"


def _natural_key(s: str) -> list:
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s or "")]


_PA_REFRESH_SUFFIX_RE = re.compile(r"-process-architect-refresh-(.+)$")
_PA_FAILURE_FIX_SUFFIX = "-process-architect"


def _classify_pa_dir(pa_dir_name: str, td_names_by_len: list[tuple[str, str]]) -> tuple[str | None, str, str | None]:
    """Return (task_id, kind, unit_id) for a PA workdir name, longest-prefix match."""
    for td_name, task_id in td_names_by_len:
        if not pa_dir_name.startswith(td_name):
            continue
        suffix = pa_dir_name[len(td_name):]
        m = _PA_REFRESH_SUFFIX_RE.match(suffix)
        if m:
            return task_id, "refresh", m.group(1)
        if suffix == _PA_FAILURE_FIX_SUFFIX:
            return task_id, "failure_fix", None
        return task_id, "unknown", None
    return None, "unknown", None


def _principal_model(model_usage: dict[str, Any] | None) -> str | None:
    if not isinstance(model_usage, dict) or not model_usage:
        return None
    best: tuple[str, float] | None = None
    for name, stats in model_usage.items():
        if not isinstance(stats, dict):
            continue
        cost = float(stats.get("costUSD") or 0.0)
        if best is None or cost > best[1]:
            best = (name, cost)
    return best[0] if best else None


def _load_pa_result(pa_dir: Path) -> dict[str, Any]:
    """Parse pa-result.json (single-line stream-json result) into a metrics dict.

    Falls back to a placeholder record when the file is missing or malformed —
    surfaces "no PA result was produced" rather than dropping the workdir.

    Also reads `pa-output/pa-decision.json` and `conflict-history.json` to
    surface which BP(s) PA touched and what the conflict outcome was — so
    the aggregate report shows "what was fixed" even when ScoreEntry's
    `process_architect_created_versions` is empty (background-PA case).
    """
    result_path = pa_dir / "pa-result.json"
    job: dict[str, Any] = {
        "pa_dir": str(pa_dir),
        "terminal_status": None,
        "is_error": None,
        "num_turns": None,
        "cost_usd": None,
        "duration_sec": None,
        "model": None,
        "session_id": None,
        "touched_units": [],
        "conflict_summary": None,
    }
    if not result_path.is_file():
        job["terminal_status"] = "no_result"
        _attach_decision_summary(pa_dir, job)
        return job
    try:
        text = result_path.read_text(encoding="utf-8").strip()
        obj = json.loads(text.splitlines()[-1]) if text else {}
    except (OSError, json.JSONDecodeError, IndexError):
        job["terminal_status"] = "unparseable_result"
        _attach_decision_summary(pa_dir, job)
        return job
    if not isinstance(obj, dict):
        job["terminal_status"] = "unparseable_result"
        _attach_decision_summary(pa_dir, job)
        return job
    job["terminal_status"] = obj.get("terminal_reason") or (
        "completed" if obj.get("subtype") == "success" else "failed"
    )
    job["is_error"] = bool(obj.get("is_error"))
    job["num_turns"] = obj.get("num_turns")
    job["cost_usd"] = obj.get("total_cost_usd")
    duration_ms = obj.get("duration_ms")
    job["duration_sec"] = int(duration_ms) // 1000 if isinstance(duration_ms, (int, float)) else None
    job["model"] = _principal_model(obj.get("modelUsage"))
    job["session_id"] = obj.get("session_id")
    _attach_decision_summary(pa_dir, job)
    return job


def _attach_decision_summary(pa_dir: Path, job: dict[str, Any]) -> None:
    """Populate `touched_units` and `conflict_summary` on the job dict.

    `touched_units`: list of `{unit_id, outcome}` — outcome ∈
    {"written", "extended", "replaced", "subsumed"}. Source: changes[]
    and subsumed[] in pa-output/pa-decision.json.

    `conflict_summary`: short string for the aggregate table.
      - None if no conflict happened.
      - "extended v0009→v0010" / "replaced v0009→v0010" /
        "subsumed (other PA wrote v0010)" — when PA reconciled.
      - "unresolved (1 retry)" — when terminal_status was conflict_unresolved.
    """
    touched: list[dict[str, str]] = []
    decision_path = pa_dir / "pa-output" / "pa-decision.json"
    decision: dict[str, Any] | None = None
    if decision_path.is_file():
        try:
            data = json.loads(decision_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                decision = data
        except (OSError, json.JSONDecodeError):
            decision = None
    if decision is not None:
        for ch in decision.get("changes") or []:
            if not isinstance(ch, dict):
                continue
            uid = ch.get("unit_id")
            if not isinstance(uid, str):
                continue
            cr = ch.get("conflict_resolution")
            if isinstance(cr, dict) and cr.get("outcome") in ("extended", "replaced"):
                touched.append({"unit_id": uid, "outcome": cr["outcome"]})
            else:
                touched.append({"unit_id": uid, "outcome": "written"})
        for su in decision.get("subsumed") or []:
            if not isinstance(su, dict):
                continue
            uid = su.get("unit_id")
            if isinstance(uid, str):
                touched.append({"unit_id": uid, "outcome": "subsumed"})
    job["touched_units"] = touched

    # Conflict summary: derive from conflict-history.json + decision.
    hist_path = pa_dir / "conflict-history.json"
    if not hist_path.is_file():
        return
    try:
        hist = json.loads(hist_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    retries = (hist or {}).get("retries") or []
    if not retries:
        return
    # If PA never recovered from conflict, mark unresolved with retry count.
    if job.get("terminal_status") == "conflict_unresolved":
        job["conflict_summary"] = f"unresolved ({len(retries)} retry)"
        return
    # Otherwise pick outcomes per conflicted unit from the decision.
    conflicted_units: dict[str, dict[str, str]] = {}
    for block in retries:
        for c in block.get("conflicts") or []:
            uid = c.get("unit_id")
            if not isinstance(uid, str):
                continue
            conflicted_units[uid] = {
                "original_base": c.get("original_base", "?"),
                "current_latest": c.get("current_latest", "?"),
            }
    if not conflicted_units:
        return
    outcomes_by_unit = {t["unit_id"]: t.get("outcome") for t in touched}
    parts: list[str] = []
    for uid, info in conflicted_units.items():
        oc = outcomes_by_unit.get(uid) or "subsumed"
        parts.append(
            f"{uid}: {oc} ({info['original_base']}→{info['current_latest']})"
        )
    job["conflict_summary"] = "; ".join(parts)


def collect_pa_metrics(summary: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    """Walk run_dir for PA workdirs, parse pa-result.json, attach metrics.

    Mutates summary in place:
    - Each task entry gets `process_architect_jobs`: list of per-job records
      (cost, turns, duration, kind, unit_id, status, model).
    - Top level gets `process_architect_totals` with aggregates.

    Picks up both `failure_fix` workdirs (post-FAIL PA runs) and async
    `refresh` workdirs (resolver-spawned PA refreshes for stale deps),
    matching each back to its originating task by longest task_dir-name
    prefix.
    """
    tasks: list[dict[str, Any]] = list(summary.get("tasks") or [])
    td_names_by_len: list[tuple[str, str]] = []
    for t in tasks:
        td = t.get("task_dir") or ""
        tid = t.get("task_id") or ""
        if not td or not tid:
            continue
        td_names_by_len.append((Path(td).name, tid))
    td_names_by_len.sort(key=lambda kv: len(kv[0]), reverse=True)

    by_task: dict[str, list[dict[str, Any]]] = {tid: [] for _, tid in td_names_by_len}
    orphans: list[dict[str, Any]] = []
    totals: dict[str, Any] = {
        "jobs": 0,
        "by_kind": {"failure_fix": 0, "refresh": 0, "unknown": 0},
        "by_status": {},
        "cost_usd": 0.0,
        "num_turns": 0,
        "duration_sec": 0,
    }

    if run_dir.is_dir():
        for entry in sorted(run_dir.iterdir()):
            if not entry.is_dir() or "-process-architect" not in entry.name:
                continue
            task_id, kind, unit_id = _classify_pa_dir(entry.name, td_names_by_len)
            job = _load_pa_result(entry)
            job["kind"] = kind
            job["unit_id"] = unit_id

            totals["jobs"] += 1
            totals["by_kind"][kind] = totals["by_kind"].get(kind, 0) + 1
            st = job.get("terminal_status") or "unknown"
            totals["by_status"][st] = totals["by_status"].get(st, 0) + 1
            if job.get("cost_usd") is not None:
                totals["cost_usd"] += float(job["cost_usd"])
            if job.get("num_turns") is not None:
                totals["num_turns"] += int(job["num_turns"])
            if job.get("duration_sec") is not None:
                totals["duration_sec"] += int(job["duration_sec"])

            if task_id and task_id in by_task:
                by_task[task_id].append(job)
            else:
                job["task_id"] = task_id
                orphans.append(job)

    for t in tasks:
        tid = t.get("task_id") or ""
        t["process_architect_jobs"] = by_task.get(tid, [])
    summary["process_architect_totals"] = totals
    if orphans:
        summary["process_architect_orphans"] = orphans
    return totals


_PA_KIND_ICON = {"failure_fix": "⚙", "refresh": "↻", "unknown": "?"}


def _pa_unit_label(job: dict[str, Any], task_entry: dict[str, Any] | None) -> str:
    """Compact "unit@version" label for a PA job row."""
    unit_id = job.get("unit_id")
    if job.get("kind") == "refresh" and unit_id:
        return f"`{unit_id}`"
    if job.get("kind") == "failure_fix" and task_entry is not None:
        created = task_entry.get("process_architect_created_versions") or []
        if created:
            parts = [f"`{c.get('unit_id')}@{c.get('version')}`" for c in created]
            return ", ".join(parts)
        return "—"
    return f"`{unit_id}`" if unit_id else "—"


def _build_pa_section(summary: dict[str, Any], tasks: list[dict[str, Any]]) -> list[str]:
    totals = summary.get("process_architect_totals") or {}
    if not totals or not totals.get("jobs"):
        return ["## Process Architect", "", "_No PA jobs ran this run._", ""]

    by_kind = totals.get("by_kind") or {}
    by_status = totals.get("by_status") or {}
    kind_parts = ", ".join(
        f"{k}={v}" for k, v in by_kind.items() if v
    ) or "—"
    status_parts = ", ".join(
        f"{k}={v}" for k, v in by_status.items() if v
    ) or "—"

    lines: list[str] = [
        "## Process Architect",
        "",
        f"- jobs: {totals.get('jobs', 0)} ({kind_parts})",
        f"- terminal status: {status_parts}",
        f"- totals: turns={int(totals.get('num_turns') or 0)} · "
        f"cpu={int(totals.get('duration_sec') or 0)}s · "
        f"cost={_fmt_cost(totals.get('cost_usd') or 0)}",
        "",
        "| task | kind | unit(s) | status | model | turns | cost | time |",
        "|---|---|---|---|---|---:|---:|---:|",
    ]
    rows: list[tuple[list[Any], str]] = []
    for t in tasks:
        for job in t.get("process_architect_jobs") or []:
            kind = job.get("kind", "?")
            row = "| `{tid}` | {kicon} {kind} | {unit} | {status} | {model} | {turns} | {cost} | {time}s |".format(
                tid=t.get("task_id", ""),
                kicon=_PA_KIND_ICON.get(kind, "?"),
                kind=kind,
                unit=_pa_unit_label(job, t),
                status=job.get("terminal_status") or "?",
                model=f"`{job.get('model')}`" if job.get("model") else "—",
                turns=job.get("num_turns") if job.get("num_turns") is not None else "?",
                cost=_fmt_cost(job.get("cost_usd")),
                time=job.get("duration_sec") if job.get("duration_sec") is not None else "?",
            )
            rows.append((_natural_key(t.get("task_id", "")), row))
    for job in summary.get("process_architect_orphans") or []:
        kind = job.get("kind", "?")
        row = "| _(orphan)_ | {kicon} {kind} | {unit} | {status} | {model} | {turns} | {cost} | {time}s |".format(
            kicon=_PA_KIND_ICON.get(kind, "?"),
            kind=kind,
            unit=f"`{job.get('unit_id')}`" if job.get("unit_id") else "—",
            status=job.get("terminal_status") or "?",
            model=f"`{job.get('model')}`" if job.get("model") else "—",
            turns=job.get("num_turns") if job.get("num_turns") is not None else "?",
            cost=_fmt_cost(job.get("cost_usd")),
            time=job.get("duration_sec") if job.get("duration_sec") is not None else "?",
        )
        rows.append(([], row))
    rows.sort(key=lambda kv: kv[0])
    lines.extend(r for _, r in rows)
    lines.append("")
    return lines


def _build_instruction_versions_section(tasks: list[dict[str, Any]]) -> list[str]:
    """Aggregate selected_version per instruction unit across all trials.

    Order follows the first task's instruction_units (= registry order).
    Single-version units render as a flat unit/version table; mixed units
    show the per-version distribution inline.
    """
    if not tasks:
        return []
    by_unit: dict[str, Counter] = {}
    for t in tasks:
        for u in t.get("instruction_units") or []:
            uid = u.get("unit_id")
            ver = u.get("selected_version") or "?"
            if not uid:
                continue
            by_unit.setdefault(uid, Counter())[ver] += 1
    if not by_unit:
        return []
    total = len(tasks)
    all_uniform = all(
        len(c) == 1 and next(iter(c.values())) == total for c in by_unit.values()
    )
    out: list[str] = []
    if all_uniform:
        out.append(f"## Instruction versions (all {total} trials identical)")
        out.append("")
        out.append("| unit | version |")
        out.append("|---|---|")
        for uid, c in by_unit.items():
            out.append(f"| `{uid}` | `{next(iter(c))}` |")
    else:
        out.append("## Instruction versions")
        out.append("")
        out.append("| unit | versions |")
        out.append("|---|---|")
        for uid, c in by_unit.items():
            parts = [f"`{v}` ×{n}" for v, n in c.most_common()]
            out.append(f"| `{uid}` | {', '.join(parts)} |")
    out.append("")
    return out


def build_report(summary: dict[str, Any]) -> str:
    tasks = list(summary.get("tasks") or [])
    tasks.sort(key=lambda t: _natural_key(t.get("task_id", "")))
    hints_by_task: dict[str, str] = summary.get("hints_by_task") or {}

    scored = [t for t in tasks if t.get("score") is not None]
    passed = [t for t in scored if t["score"] == 1]
    avg = (sum(t["score"] for t in scored) / len(scored)) if scored else None
    total_cost = sum(
        float(t["cost_usd"]) for t in tasks if t.get("cost_usd") is not None
    )
    total_turns = sum(
        int(t["num_turns"]) for t in tasks if t.get("num_turns") is not None
    )
    total_mcp = sum(int(t.get("mcp_calls") or 0) for t in tasks)
    cpu_sec = sum(int(t.get("duration_sec") or 0) for t in tasks)
    trial_sec_sum = sum(int(t.get("trial_sec") or 0) for t in tasks)
    boot_sec_sum = sum(int(t.get("bootstrap_sec") or 0) for t in tasks)

    pa_totals = summary.get("process_architect_totals") or {}
    pa_cost = float(pa_totals.get("cost_usd") or 0.0)
    pa_turns = int(pa_totals.get("num_turns") or 0)
    pa_duration = int(pa_totals.get("duration_sec") or 0)
    pa_jobs_count = int(pa_totals.get("jobs") or 0)
    grand_total = total_cost + pa_cost

    harness_run_id = summary.get("harness_run_id") or ""
    out: list[str] = [
        f"# Run report — {summary.get('run_id', '')}",
        "",
        *([f"- run id (harness): `{harness_run_id}`"] if harness_run_id else []),
        f"- benchmark: `{summary.get('benchmark', '')}`",
        f"- run name:  `{summary.get('run_name', '')}`",
        f"- model:     `{summary.get('model', '')}`",
        f"- effort:    `{summary.get('effort', '')}`",
        f"- concurrency: {summary.get('concurrency', '')}",
        f"- wall-clock: {_fmt_hms(summary.get('wall_clock_sec', 0))} · "
        f"cpu-sum: {_fmt_hms(cpu_sec)} · "
        f"trial-sum: {_fmt_hms(trial_sec_sum)} · "
        f"boot-sum: {_fmt_hms(boot_sec_sum)}",
        f"- tasks: {len(tasks)} total · {len(scored)} scored · {len(passed)} passed"
        + (f" · avg **{avg * 100:.1f}%**" if avg is not None else ""),
        f"- executor: turns={total_turns} · mcp={total_mcp} · cost={_fmt_cost(total_cost)}",
        f"- process architect: jobs={pa_jobs_count} · turns={pa_turns} · "
        f"cpu={pa_duration}s · cost={_fmt_cost(pa_cost)}",
        f"- grand-total cost (executor + PA): **{_fmt_cost(grand_total)}**",
        "",
    ]
    out.extend(_build_instruction_versions_section(tasks))
    out.extend([
        "## Per-task",
        "",
        "| # | task | hint | bp | score | outcome | turns | mcp | cost | boot | time | trial-time | notes |",
        "|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ])
    for t in tasks:
        hint = hints_by_task.get(t.get("task_id", ""), "")
        bp = str(t.get("business_process") or "").replace("|", "\\|")
        bp_cell = f"`{bp}`" if bp else "—"
        notes = "; ".join(t.get("score_detail") or [])
        notes_compact = (notes or "").replace("|", "\\|").replace("\n", " ↵ ")
        out.append(
            "| {icon} | `{tid}` | {hint} | {bp} | {score} | {outcome} | {turns} | {mcp} | {cost} | {boot}s | {time}s | {trial}s | {notes} |".format(
                icon=_icon(t.get("score")),
                tid=t.get("task_id", ""),
                hint=hint,
                bp=bp_cell,
                score=_fmt_score(t.get("score")),
                outcome=_short_outcome(t.get("answer_outcome", "")),
                turns=t.get("num_turns") if t.get("num_turns") is not None else "?",
                mcp=t.get("mcp_calls", "?"),
                cost=_fmt_cost(t.get("cost_usd")),
                boot=int(t.get("bootstrap_sec") or 0),
                time=t.get("duration_sec", 0),
                trial=int(t.get("trial_sec") or 0),
                notes=notes_compact,
            )
        )
    out.append("")
    out.extend(_build_pa_section(summary, tasks))
    out.append("## Artifact paths")
    out.append("")
    out.append(
        "Each task dir contains `CLAUDE.md`, `task.md`, `tree.md`, `vault/`, "
        "`bin-help/`, `business_processes/`, `runtime_prelude.py`, `workspace.py`, "
        "`scratchpad.json`, `state.json`, `answer.json`, `result.json`. "
        "`result.json` records the trial timeline as `start_trial_at` / "
        "`bootstrap_started_at` / `bootstrap_finished_at` / `end_trial_at` "
        "(POSIX seconds), plus pre-computed `bootstrap_sec` and `trial_sec`. "
        "Stream/audit logs live under `.logs/` "
        "(`transcript.jsonl`, `claude-stderr.log`, `python/`, "
        "`mcp-tool-calls.jsonl`, `executor_actions.md`, "
        "`pre-bootstrap-manifest.json`, `bin-help-manifest.json`)."
    )
    out.append("")
    for t in tasks:
        out.append(f"- `{t.get('task_id')}` → `{t.get('task_dir', '')}`")
    out.append("")
    return "\n".join(out)


def write_report(summary: dict[str, Any], run_dir: Path) -> Path:
    text = build_report(summary)
    out_path = run_dir / "report.md"
    out_path.write_text(text, encoding="utf-8")
    return out_path


def write_summary(summary: dict[str, Any], run_dir: Path) -> Path:
    out_path = run_dir / "summary.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return out_path


def write_pa_aggregate_report(summary: dict[str, Any], run_dir: Path) -> Path:
    """Aggregate every per-PA `report_PA.md` into `run_dir/report_PA.md`.

    Each PA workdir under run_dir gets a row with link to its own
    `report_PA.md`. Quickly answers "which PA jobs ran this run and where
    do I look for details" without opening individual `pa-result.json`.
    """
    tasks: list[dict[str, Any]] = list(summary.get("tasks") or [])
    totals = summary.get("process_architect_totals") or {}
    orphans: list[dict[str, Any]] = summary.get("process_architect_orphans") or []

    lines: list[str] = [
        "# Process Architect — run aggregate",
        "",
        f"- run_id: `{summary.get('run_id', '?')}`",
        *(
            [f"- run id (harness): `{summary.get('harness_run_id')}`"]
            if summary.get("harness_run_id")
            else []
        ),
        f"- jobs: {totals.get('jobs', 0)}",
    ]
    by_kind = totals.get("by_kind") or {}
    by_status = totals.get("by_status") or {}
    if by_kind:
        kind_parts = ", ".join(f"{k}={v}" for k, v in by_kind.items() if v)
        lines.append(f"- by kind: {kind_parts}")
    if by_status:
        status_parts = ", ".join(f"{k}={v}" for k, v in by_status.items() if v)
        lines.append(f"- by status: {status_parts}")
    lines.append(
        f"- totals: turns={int(totals.get('num_turns') or 0)} · "
        f"cpu={int(totals.get('duration_sec') or 0)}s · "
        f"cost={_fmt_cost(totals.get('cost_usd') or 0)}"
    )
    lines.append("")
    lines.append(
        "| task | kind | unit(s) (outcome) | conflict | status | turns | cost | time | report |"
    )
    lines.append("|---|---|---|---|---|---:|---:|---:|---|")

    def _report_link(pa_dir_str: str | None) -> str:
        if not pa_dir_str:
            return "—"
        pa_path = Path(pa_dir_str)
        try:
            rel = pa_path.relative_to(run_dir) / "report_PA.md"
        except ValueError:
            rel = pa_path / "report_PA.md"
        if (run_dir / rel).is_file():
            return f"[report_PA.md]({rel})"
        return "_(no report)_"

    def _units_label(job: dict[str, Any], task_entry: dict[str, Any] | None) -> str:
        # Prefer decision-based touched_units (covers background PAs, where
        # ScoreEntry's process_architect_created_versions is empty).
        touched = job.get("touched_units") or []
        if touched:
            parts = []
            for t in touched:
                uid = t.get("unit_id", "?")
                outcome = t.get("outcome", "?")
                parts.append(f"`{uid}` _{outcome}_")
            return ", ".join(parts)
        return _pa_unit_label(job, task_entry)

    tasks_sorted = sorted(tasks, key=lambda t: _natural_key(t.get("task_id", "")))
    for t in tasks_sorted:
        for job in t.get("process_architect_jobs") or []:
            kind = job.get("kind", "?")
            unit = _units_label(job, t)
            conflict = job.get("conflict_summary") or "—"
            status = job.get("terminal_status") or "?"
            turns = job.get("num_turns") if job.get("num_turns") is not None else "?"
            cost = _fmt_cost(job.get("cost_usd"))
            dur = job.get("duration_sec") if job.get("duration_sec") is not None else "?"
            link = _report_link(job.get("pa_dir"))
            lines.append(
                f"| `{t.get('task_id', '')}` | {kind} | {unit} | {conflict} | "
                f"{status} | {turns} | {cost} | {dur}s | {link} |"
            )
    for job in orphans:
        kind = job.get("kind", "?")
        unit = _units_label(job, None)
        conflict = job.get("conflict_summary") or "—"
        status = job.get("terminal_status") or "?"
        turns = job.get("num_turns") if job.get("num_turns") is not None else "?"
        cost = _fmt_cost(job.get("cost_usd"))
        dur = job.get("duration_sec") if job.get("duration_sec") is not None else "?"
        link = _report_link(job.get("pa_dir"))
        lines.append(
            f"| _(orphan)_ | {kind} | {unit} | {conflict} | "
            f"{status} | {turns} | {cost} | {dur}s | {link} |"
        )
    lines.append("")

    out_path = run_dir / "report_PA.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
