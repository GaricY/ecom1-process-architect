"""Prelude exec'd at the top of every `execute_python` snippet.

The MCP server prepends a one-line `exec(open("runtime_prelude.py").read())`
to whatever code the agent submits, so this file is always loaded first.

Exposes:
  - `ws` — Workspace instance (read/write/exec/answer surface).
  - `scratchpad` — persistent dict loaded from scratchpad.json; saved on exit.
  - `state` — persistent JSON dict for working values between calls.
  - `submit_and_exit(message, outcome, refs, verify=None)` — preferred terminal.

Stdlib + a small set of conveniences are pre-imported so snippets stay short.
"""

import json, sys, os, re, csv, math, hashlib, base64, atexit  # noqa: F401,E401
from datetime import datetime, timedelta, date  # noqa: F401
from collections import defaultdict, Counter  # noqa: F401
from pathlib import PurePosixPath  # noqa: F401

try:
    import yaml  # noqa: F401
except Exception:
    yaml = None  # noqa: F841

try:
    from dateutil import parser as dateutil_parser  # noqa: F401
    from dateutil.relativedelta import relativedelta  # noqa: F401
except Exception:
    dateutil_parser = None  # noqa: F841
    relativedelta = None  # noqa: F841

from workspace import Workspace  # noqa: E402

ws = Workspace()

_SCRATCHPAD_PATH = os.environ.get("ECOM_SCRATCHPAD_PATH") or "scratchpad.json"
_STATE_PATH = os.environ.get("ECOM_STATE_PATH") or "state.json"
_ANSWER_PATH = os.environ.get("ECOM_ANSWER_PATH") or "answer.json"


def _load_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return default
        return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def _save_json(path: str, value: dict) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(value, f, indent=2, default=str)
            f.flush()
            os.fsync(f.fileno())
    except Exception as _exc:  # noqa: F841
        print(f"[runtime] failed to save {path}: {_exc}", file=sys.stderr)


scratchpad: dict = _load_json(_SCRATCHPAD_PATH, {"refs": []})
if "refs" not in scratchpad or not isinstance(scratchpad.get("refs"), list):
    scratchpad["refs"] = []

state: dict = _load_json(_STATE_PATH, {})


def _save_all_on_exit():
    _save_json(_SCRATCHPAD_PATH, scratchpad)
    _save_json(_STATE_PATH, state)


atexit.register(_save_all_on_exit)


def _answer_was_submitted() -> bool:
    return os.path.isfile(_ANSWER_PATH)


def submit_and_exit(
    message: str | None = None,
    outcome: str | None = None,
    refs: list | None = None,
    verify_fn=None,
):
    """Merge answer/outcome/refs into scratchpad, call ws.answer, exit(0).

    Preferred terminal for every task. Direct ws.answer() still works but the
    agent should call submit_and_exit so it does not run more runtime
    mutations after the answer was recorded.
    """
    if message is not None:
        scratchpad["answer"] = message
        scratchpad["message"] = message
    if outcome is not None:
        scratchpad["outcome"] = outcome
    if refs is not None:
        merged = list(scratchpad.get("refs") or [])
        for r in refs:
            if isinstance(r, str) and r not in merged:
                merged.append(r)
        scratchpad["refs"] = merged
    scratchpad["refs"] = list(dict.fromkeys(scratchpad.get("refs") or []))

    if verify_fn is None:
        def verify_fn(sp):
            return (
                "answer" in sp
                and isinstance(sp.get("refs"), list)
                and sp.get("outcome") in {
                    "OUTCOME_OK",
                    "OUTCOME_DENIED_SECURITY",
                    "OUTCOME_NONE_CLARIFICATION",
                    "OUTCOME_NONE_UNSUPPORTED",
                    "OUTCOME_ERR_INTERNAL",
                }
            )

    ws.answer(scratchpad, verify_fn)
    raise SystemExit(0)
