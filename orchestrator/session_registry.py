"""Opaque session-id ↔ harness URL registry.

The orchestrator allocates a fresh `ECOM_SESSION_ID` for every trial and
stores its `harness_url` in a JSON file under
`<run_root>/.sessions/<session_id>.json`. The MCP server reads it back at
spawn time. Neither the Claude CLI process nor any task-directory file gets
to see the raw URL, which keeps it out of transcripts and logs.

The directory lives at the run root, outside the per-trial task directory,
so `.claude/settings.json` deny rules (`Read(../**)`) block Claude from
reading other trials' session files.
"""

from __future__ import annotations

import contextlib
import json
import os
import secrets
import time
from pathlib import Path

ENV_SESSION_ID = "ECOM_SESSION_ID"
ENV_SESSIONS_DIR = "ECOM_SESSIONS_DIR"
ENV_ANSWER_PATH = "ECOM_ANSWER_PATH"
ENV_TASK_DIR = "ECOM_TASK_DIR"
ENV_PYTHON_DIR = "ECOM_PYTHON_DIR"
ENV_SCRATCHPAD_PATH = "ECOM_SCRATCHPAD_PATH"
ENV_STATE_PATH = "ECOM_STATE_PATH"
ENV_TOOL_CALLS_PATH = "ECOM_TOOL_CALLS_PATH"
ENV_RUNTIME_PRELUDE = "ECOM_RUNTIME_PRELUDE"


def _sessions_dir(run_root: Path) -> Path:
    return run_root / ".sessions"


def new_session_id() -> str:
    return f"sess_{secrets.token_urlsafe(16)}"


def register(
    *,
    run_root: Path,
    session_id: str,
    payload: dict,
) -> Path:
    """Persist `payload` under <run_root>/.sessions/<session_id>.json.

    Returns the file path. Caller is expected to populate at minimum:
        - harness_url
        - task_dir
        - answer_path
        - python_dir
        - scratchpad_path
        - state_path
        - tool_calls_path
        - runtime_prelude_path
    """
    sessions = _sessions_dir(run_root)
    sessions.mkdir(parents=True, exist_ok=True)
    out = sessions / f"{session_id}.json"
    body = {**payload, "created_at": time.time()}
    out.write_text(json.dumps(body), encoding="utf-8")
    try:
        os.chmod(out, 0o600)
    except OSError:
        pass
    return out


def load(*, sessions_dir: Path, session_id: str) -> dict:
    path = sessions_dir / f"{session_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"session registry entry not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def clear(*, run_root: Path, session_id: str) -> None:
    with contextlib.suppress(FileNotFoundError, OSError):
        (_sessions_dir(run_root) / f"{session_id}.json").unlink()


def sessions_dir(run_root: Path) -> Path:
    return _sessions_dir(run_root)
