"""Snippet runner used by the MCP `execute_python` tool.

Saves each snippet as `.logs/python/execute_NNNN.py`, prepends the runtime
prelude loader so the agent doesn't need to remember it, spawns it as a
subprocess with the BitGN runtime env, and captures stdout/stderr/exit_code.

The harness URL stays in the subprocess env only — Claude never sees it.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

PRELUDE_HEADER = (
    "# Auto-prepended by execute_python; do not duplicate exec().\n"
    "exec(open('runtime_prelude.py').read())\n"
    "# --- agent code below ---\n"
)

# Per-task aggregator filename and per-entry cap. Full stderr lives in
# `.logs/python/execute_NNNN.stderr`; this aggregator gives the user a
# single scrollable view of every anomaly without browsing 100+ files.
_ERRORS_LOG = "errors.md"
_AGG_STDERR_CAP = 2000


def _append_errors_log(
    *,
    python_dir: Path,
    idx: int,
    exit_code: int,
    stderr: str,
) -> None:
    """Append a snippet anomaly to <python_dir>/../errors.md.

    Triggers on non-empty stderr OR exit_code != 0. Best-effort: any IO
    failure is swallowed so the aggregator can never break a snippet.
    """
    if not stderr.strip() and exit_code == 0:
        return
    body = stderr.rstrip() or f"(no stderr, exit_code={exit_code})"
    if len(body) > _AGG_STDERR_CAP:
        body = (
            body[:_AGG_STDERR_CAP].rstrip()
            + f"\n…[truncated, full stderr in .logs/python/execute_{idx:04d}.stderr]"
        )
    ts = time.strftime("%H:%M:%S")
    entry = (
        f"## execute_{idx:04d}  exit={exit_code}  [{ts}]\n\n"
        "```\n"
        f"{body}\n"
        "```\n\n"
    )
    # `.logs/python/` → parent is `.logs/`, where we want the aggregator.
    logs_dir = python_dir.parent
    target = logs_dir / _ERRORS_LOG
    with contextlib.suppress(OSError):
        logs_dir.mkdir(parents=True, exist_ok=True)
        with open(target, "a", encoding="utf-8") as fh:
            fh.write(entry)


@dataclass
class ExecuteResult:
    exit_code: int
    stdout: str
    stderr: str
    snippet_path: str
    scratchpad_excerpt: str
    answer_submitted: bool


def _next_index(python_dir: Path) -> int:
    if not python_dir.is_dir():
        return 1
    max_idx = 0
    pat = re.compile(r"^execute_(\d+)\.py$")
    for entry in python_dir.iterdir():
        m = pat.match(entry.name)
        if m:
            max_idx = max(max_idx, int(m.group(1)))
    return max_idx + 1


def _scrub(text: str, secrets: list[str]) -> str:
    out = text
    for secret in secrets:
        if not secret:
            continue
        out = out.replace(secret, "[REDACTED]")
    return out


def _scratchpad_excerpt(scratchpad_path: Path, max_bytes: int = 4000) -> str:
    try:
        raw = scratchpad_path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return ""
    if len(raw) <= max_bytes:
        return raw
    return raw[: max_bytes - 12] + "…[truncated]"


def execute_python(
    *,
    code: str,
    task_dir: Path,
    python_dir: Path,
    answer_path: Path,
    scratchpad_path: Path,
    state_path: Path,
    tool_calls_path: Path,
    runtime_prelude_path: Path,
    harness_url: str,
    python_bin: str,
    extra_env: dict[str, str] | None = None,
    timeout_sec: int = 180,
    scrub_secrets: list[str] | None = None,
) -> ExecuteResult:
    """Save snippet, run it, return ExecuteResult.

    `scrub_secrets` is a list of strings (e.g. the live harness URL) that are
    replaced with `[REDACTED]` in stdout/stderr before they're returned to
    the MCP caller. This is the last-line defence against secret leak in
    Claude transcript.
    """
    python_dir.mkdir(parents=True, exist_ok=True)
    idx = _next_index(python_dir)
    snippet_path = python_dir / f"execute_{idx:04d}.py"

    body = PRELUDE_HEADER + (code if code.endswith("\n") else code + "\n")
    snippet_path.write_text(body, encoding="utf-8")

    # Snippet-start marker so executor_log.py can group inner tool calls
    # by snippet without inferring timing.
    try:
        with open(tool_calls_path, "a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "_marker": "snippet_start",
                        "idx": idx,
                        "snippet": snippet_path.name,
                    }
                )
                + "\n"
            )
    except OSError:
        pass

    env = {**os.environ}
    if extra_env:
        env.update(extra_env)
    # workspace.py / runtime_prelude.py live in task_dir; Python's default
    # import path is the script's directory (python/), not cwd — without
    # this the runtime_prelude.py's `from workspace import Workspace` fails
    # and the agent burns several snippets debugging an env issue.
    env["PYTHONPATH"] = str(task_dir) + os.pathsep + env.get("PYTHONPATH", "")
    env["RUNTIME_HARNESS_URL"] = harness_url
    env["ECOM_ANSWER_PATH"] = str(answer_path)
    env["ECOM_SCRATCHPAD_PATH"] = str(scratchpad_path)
    env["ECOM_STATE_PATH"] = str(state_path)
    env["ECOM_TOOL_CALLS_PATH"] = str(tool_calls_path)
    env["ECOM_RUNTIME_PRELUDE"] = str(runtime_prelude_path)

    # cwd=task_dir so runtime_prelude.py / workspace.py / scratchpad.json
    # resolve as the prelude expects. Pass the snippet by its task-dir-relative
    # path (`.logs/python/execute_NNNN.py`).
    rel_snippet = snippet_path.relative_to(task_dir)
    proc = subprocess.run(
        [python_bin, str(rel_snippet)],
        cwd=str(task_dir),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        check=False,
    )

    secrets = list(scrub_secrets or [])
    stdout = _scrub(proc.stdout or "", secrets)
    stderr = _scrub(proc.stderr or "", secrets)

    # Mirror stdout/stderr next to the snippet for offline forensics.
    (python_dir / f"execute_{idx:04d}.stdout").write_text(stdout, encoding="utf-8")
    (python_dir / f"execute_{idx:04d}.stderr").write_text(stderr, encoding="utf-8")

    # Aggregate anomalies for at-a-glance scanning across all snippets.
    _append_errors_log(
        python_dir=python_dir,
        idx=idx,
        exit_code=proc.returncode,
        stderr=stderr,
    )

    return ExecuteResult(
        exit_code=proc.returncode,
        stdout=stdout,
        stderr=stderr,
        snippet_path=str(snippet_path),
        scratchpad_excerpt=_scratchpad_excerpt(scratchpad_path),
        answer_submitted=answer_path.is_file(),
    )


def render_result_text(result: ExecuteResult) -> str:
    """Compact human/agent-readable rendering returned by the MCP tool."""
    parts: list[str] = []
    parts.append(f"exit_code={result.exit_code}")
    parts.append(f"snippet={result.snippet_path}")
    parts.append(f"answer_submitted={str(result.answer_submitted).lower()}")
    if result.stdout.strip():
        parts.append("stdout:\n" + result.stdout.rstrip())
    if result.stderr.strip():
        parts.append("stderr:\n" + result.stderr.rstrip())
    if result.scratchpad_excerpt.strip():
        parts.append("scratchpad:\n" + result.scratchpad_excerpt.rstrip())
    return "\n".join(parts)
