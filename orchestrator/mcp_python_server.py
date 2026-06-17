"""Stdio MCP server exposing a single tool: `execute_python`.

Wired up so Claude CLI in a per-trial task directory has exactly one runtime
boundary. The orchestrator allocates an opaque `ECOM_SESSION_ID` per trial,
writes session metadata (harness URL + paths) into the session registry,
then launches the Claude CLI process with `ECOM_SESSION_ID` and
`ECOM_SESSIONS_DIR` in env. Claude CLI spawns this server as a subprocess
via `.claude/settings.json` and inherits the env. The server looks up the
trial's harness URL and never writes it into the task directory.

`execute_python(code: str)` returns:

    {
      "exit_code": int,
      "stdout": str,
      "stderr": str,
      "snippet_path": str,
      "scratchpad_excerpt": str,
      "answer_submitted": bool,
    }
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .python_executor import execute_python as _execute_python
from .session_registry import (
    ENV_SESSION_ID,
    ENV_SESSIONS_DIR,
    load as load_session,
)


def _log(msg: str) -> None:
    line = f"[ecom-mcp {time.strftime('%H:%M:%S')}] {msg}"
    print(line, file=sys.stderr, flush=True)


def _required_env(key: str) -> str:
    value = os.environ.get(key, "")
    if not value:
        _log(f"FATAL: {key} not set")
        raise SystemExit(2)
    return value


SESSION_ID = _required_env(ENV_SESSION_ID)
SESSIONS_DIR = Path(_required_env(ENV_SESSIONS_DIR))

try:
    SESSION = load_session(sessions_dir=SESSIONS_DIR, session_id=SESSION_ID)
except FileNotFoundError as exc:
    _log(f"FATAL: session registry miss: {exc}")
    raise SystemExit(2) from exc

HARNESS_URL: str = SESSION["harness_url"]
TASK_DIR = Path(SESSION["task_dir"]).resolve()
PYTHON_DIR = Path(SESSION["python_dir"]).resolve()
ANSWER_PATH = Path(SESSION["answer_path"]).resolve()
SCRATCHPAD_PATH = Path(SESSION["scratchpad_path"]).resolve()
STATE_PATH = Path(SESSION["state_path"]).resolve()
TOOL_CALLS_PATH = Path(SESSION["tool_calls_path"]).resolve()
RUNTIME_PRELUDE = Path(SESSION["runtime_prelude_path"]).resolve()
PYTHON_BIN: str = SESSION.get("python_bin", "python3")
SNIPPET_TIMEOUT: int = int(SESSION.get("snippet_timeout_sec", 180))

_log(
    f"start: session={SESSION_ID[:8]}… task_dir={TASK_DIR} "
    f"python_bin={PYTHON_BIN}"
)

server = FastMCP("ecom-python")


@server.tool()
def execute_python(code: str) -> str:
    """Execute one Python snippet inside the trial runtime.

    The snippet runs with the BitGN ECOM workspace exposed as `ws`, a
    persistent `scratchpad` dict, and a persistent `state` dict. Call
    `submit_and_exit(message, outcome, refs)` to submit the final answer.

    Args:
        code: Python source. The MCP server prepends a one-line prelude
              loader, so do not `exec(open('runtime_prelude.py')...)` yourself.

    Returns a JSON string with `exit_code`, `stdout`, `stderr`,
    `snippet_path`, `scratchpad_excerpt`, and `answer_submitted`.
    """
    _log(f"execute_python(code_len={len(code)})")
    result = _execute_python(
        code=code,
        task_dir=TASK_DIR,
        python_dir=PYTHON_DIR,
        answer_path=ANSWER_PATH,
        scratchpad_path=SCRATCHPAD_PATH,
        state_path=STATE_PATH,
        tool_calls_path=TOOL_CALLS_PATH,
        runtime_prelude_path=RUNTIME_PRELUDE,
        harness_url=HARNESS_URL,
        python_bin=PYTHON_BIN,
        timeout_sec=SNIPPET_TIMEOUT,
        scrub_secrets=[HARNESS_URL],
    )

    payload = {
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "snippet_path": result.snippet_path,
        "scratchpad_excerpt": result.scratchpad_excerpt,
        "answer_submitted": result.answer_submitted,
    }
    _log(
        f"  exit={result.exit_code} answer_submitted={result.answer_submitted} "
        f"stdout={len(result.stdout)}b stderr={len(result.stderr)}b"
    )
    # Return a JSON string — Claude renders it back as the tool output.
    return json.dumps(payload, indent=2)


if __name__ == "__main__":
    server.run()
