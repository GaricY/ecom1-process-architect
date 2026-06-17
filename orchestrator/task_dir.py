"""TaskMaterializer — assemble a per-trial task directory.

Wires together:
  - `bootstrap.pre_bootstrap_dump`  → fresh vault/, tree.md, static instructions.
  - `bootstrap.build_bin_help`      → bin-help/.
  - Trial-specific writeable artifacts: task.md, scratchpad.json, state.json,
    answer.json (at task_dir root); .logs/python/, .logs/mcp-tool-calls.jsonl
    (created lazily by the snippet).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .bootstrap import (
    LOGS_DIR_NAME,
    BinHelpResult,
    DumpSqlResult,
    PreBootstrapResult,
    TrialPrerender,
    build_bin_help,
    dump_sql_tables,
    fetch_trial_prerender,
    pre_bootstrap_dump,
)


@dataclass
class PreparedTaskDir:
    task_dir: Path
    logs_dir: Path
    answer_path: Path
    scratchpad_path: Path
    state_path: Path
    python_dir: Path
    runtime_prelude_path: Path
    tool_calls_path: Path
    pre_bootstrap: PreBootstrapResult
    bin_help: BinHelpResult
    trial_prerender: TrialPrerender
    dump_sql: DumpSqlResult | None = None


def _build_task_md(
    *,
    benchmark_id: str,
    task_id: str,
    trial_id: str,
    instruction: str,
) -> str:
    body = (
        f"# BitGN ECOM trial\n\n"
        f"- benchmark: {benchmark_id}\n"
        f"- task_id: {task_id}\n"
        f"- trial_id: {trial_id}\n\n"
        f"## Task instruction\n\n"
        f"<task-instruction>\n{instruction}\n</task-instruction>\n\n"
        f"## How to work in this directory\n\n"
        f"The orchestrator prepared this folder with:\n\n"
        f"- `vault/` — fresh dump of live `/docs`, `/bin`, every `AGENTS.md` and `README.md`.\n"
        f"- `tree.md` — `tree -L 2 /` snapshot at trial start.\n"
        f"- `bin-help/` — `--help` output for every `/bin/<tool>` that exists.\n"
        f"- `CLAUDE.md` — executor role, scratchpad/state contract, refs/submission.\n"
        f"- `business_processes/` — short policy reminders.\n"
        f"- `runtime_prelude.py`, `workspace.py` — Python prelude loaded by every `execute_python` snippet.\n\n"
        f"Live workspace/policy always wins over the local snapshot. All runtime\n"
        f"reads, SQL queries, `/bin/*` actions, and final answer submission go\n"
        f"through the MCP tool `execute_python` — that is the only runtime\n"
        f"boundary. Do NOT use the host shell.\n\n"
        f"Read `CLAUDE.md` first, then this file, then call `execute_python`\n"
        f"with your first Python snippet.\n"
    )
    return body


def materialize(
    *,
    harness_url: str,
    task_dir: Path,
    static_instructions_dir: Path,
    benchmark_id: str,
    task_id: str,
    trial_id: str,
    instruction: str,
    dump_sql_rows: int = 0,
    world_modes_enabled: bool = False,
) -> PreparedTaskDir:
    """Create one trial's task directory from scratch.

    When `dump_sql_rows > 0`, also dump up to that many rows per user table
    into `task_dir/dump_sql/` (see `bootstrap.dump_sql_tables`).

    `world_modes_enabled` (WORLD_CREATE_ENABLED or WORLD_REFRESH_ENABLED)
    is forwarded to `pre_bootstrap_dump` to gate the /proc tree walk — the
    proc samples/READMEs it produces feed only the world PA modes.
    """
    task_dir.mkdir(parents=True, exist_ok=True)

    pre = pre_bootstrap_dump(
        harness_url=harness_url,
        task_dir=task_dir,
        static_instructions_dir=static_instructions_dir,
        benchmark_id=benchmark_id,
        task_id=task_id,
        trial_id=trial_id,
        world_modes_enabled=world_modes_enabled,
    )

    bh = build_bin_help(
        harness_url=harness_url,
        task_dir=task_dir,
    )

    dump_sql_result: DumpSqlResult | None = None
    if dump_sql_rows > 0:
        dump_sql_result = dump_sql_tables(
            harness_url=harness_url,
            task_dir=task_dir,
            limit=dump_sql_rows,
        )

    prerender = fetch_trial_prerender(harness_url)

    task_md = _build_task_md(
        benchmark_id=benchmark_id,
        task_id=task_id,
        trial_id=trial_id,
        instruction=instruction,
    )
    (task_dir / "task.md").write_text(task_md, encoding="utf-8")

    # Working documents stay at task_dir root — agent re-reads them between
    # snippets, and they double as the human-visible final state.
    scratchpad = task_dir / "scratchpad.json"
    if not scratchpad.is_file():
        scratchpad.write_text(json.dumps({"refs": []}, indent=2), encoding="utf-8")

    state = task_dir / "state.json"
    if not state.is_file():
        state.write_text("{}", encoding="utf-8")

    # Stream/audit logs live under .logs/ to keep task_dir root uncluttered.
    logs_dir = task_dir / LOGS_DIR_NAME
    logs_dir.mkdir(parents=True, exist_ok=True)

    tool_calls_path = logs_dir / "mcp-tool-calls.jsonl"
    if not tool_calls_path.is_file():
        tool_calls_path.touch()

    python_dir = logs_dir / "python"
    python_dir.mkdir(parents=True, exist_ok=True)

    return PreparedTaskDir(
        task_dir=task_dir,
        logs_dir=logs_dir,
        answer_path=task_dir / "answer.json",
        scratchpad_path=scratchpad,
        state_path=state,
        python_dir=python_dir,
        runtime_prelude_path=task_dir / "runtime_prelude.py",
        tool_calls_path=tool_calls_path,
        pre_bootstrap=pre,
        bin_help=bh,
        trial_prerender=prerender,
        dump_sql=dump_sql_result,
    )
