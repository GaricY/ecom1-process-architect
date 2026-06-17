"""Drive the local Claude CLI inside a per-trial task directory.

The Claude CLI is invoked with `-p` + stream-json so we capture an offline
transcript. The MCP server defined in `.claude/settings.json` (or via
`--mcp-config`) is the only runtime boundary the agent has.

The orchestrator stops Claude CLI as soon as `answer.json` materialises, with
a short grace window so the closing transcript line lands on disk.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .bootstrap import LOGS_DIR_NAME

# Stream/audit logs live under task_dir/.logs/. result.json is the trial
# summary and stays at task_dir root for at-a-glance triage.
TRANSCRIPT_FILE = f"{LOGS_DIR_NAME}/transcript.jsonl"
RESULT_FILE = "result.json"
STDERR_LOG = f"{LOGS_DIR_NAME}/claude-stderr.log"


@dataclass
class ClaudeRunResult:
    exit_code: int
    duration_ms: int
    num_turns: int | None
    total_cost_usd: float | None
    is_error: bool
    stop_reason: str | None
    result_text: str | None
    session_id: str | None
    mcp_calls: int


_DEFAULT_PROMPT = (
    "Read CLAUDE.md and task.md, then solve the task. All runtime access "
    "happens via the MCP tool `mcp__ecom-python__execute_python`. When the "
    "task is complete, call submit_and_exit(...) from inside an "
    "execute_python snippet."
)


async def _watch_answer(answer_path: Path, ready: asyncio.Event) -> None:
    while not ready.is_set():
        if answer_path.is_file():
            ready.set()
            return
        await asyncio.sleep(0.5)


async def run_claude_cli(
    *,
    claude_bin: str,
    task_dir: Path,
    prompt: str,
    max_turns: int,
    effort: str,
    model: str,
    env: dict[str, str],
    answer_path: Path,
    answer_grace_sec: float = 8.0,
    overall_timeout_sec: float | None = None,
    label: str = "",
    scrub_secrets: list[str] | None = None,
    mcp_servers: dict[str, dict] | None = None,
) -> ClaudeRunResult:
    """Spawn the Claude CLI, stream stdout to transcript.jsonl, await exit.

    `mcp_servers` (when given) is written to a temp JSON file and passed via
    `--mcp-config` with `--strict-mcp-config`. The dict shape mirrors what a
    Claude `.claude/settings.json` `mcpServers` value would carry.
    """
    transcript_path = task_dir / TRANSCRIPT_FILE
    result_path = task_dir / RESULT_FILE
    stderr_path = task_dir / STDERR_LOG
    transcript_path.parent.mkdir(parents=True, exist_ok=True)

    cli_args: list[str] = [
        "-p",
        "--output-format", "stream-json",
        "--input-format", "stream-json",
        "--verbose",
        "--max-turns", str(max_turns),
        "--permission-mode", "bypassPermissions",
        "--setting-sources", "project",
        "--disable-slash-commands",
        "--effort", effort,
        "--no-session-persistence",
        "--include-partial-messages",
    ]
    if model:
        cli_args.extend(["--model", model])

    mcp_config_path: Path | None = None
    if mcp_servers:
        mcp_config_path = task_dir / ".mcp-config.json"
        mcp_config_path.write_text(
            json.dumps({"mcpServers": mcp_servers}, indent=2), encoding="utf-8"
        )
        cli_args.extend(
            [
                "--mcp-config", str(mcp_config_path),
                "--strict-mcp-config",
            ]
        )

    full_env = {**os.environ, **env}
    secrets = list(scrub_secrets or [])

    if label:
        print(f"{label} spawning claude CLI in {task_dir}")

    start = time.time()

    # Claude stream-json output can exceed asyncio's default 64KiB line
    # buffer when a single tool result is large (e.g. a long ws.sql dump
    # or a huge transcript turn). Bump the StreamReader limit to keep
    # readline() from raising "Separator is not found, and chunk exceeds
    # the limit" and killing the entire trial.
    proc = await asyncio.create_subprocess_exec(
        claude_bin,
        *cli_args,
        cwd=str(task_dir),
        env=full_env,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        limit=10 * 1024 * 1024,
    )
    assert proc.stdin and proc.stdout and proc.stderr

    user_message = {"type": "user", "message": {"role": "user", "content": prompt}}
    proc.stdin.write((json.dumps(user_message) + "\n").encode("utf-8"))
    proc.stdin.close()

    mcp_calls = 0
    last_result_line: str | None = None
    answer_seen = asyncio.Event()

    def _scrub(text: str) -> str:
        out = text
        for secret in secrets:
            if secret:
                out = out.replace(secret, "[REDACTED]")
        return out

    async def consume_stdout() -> None:
        nonlocal mcp_calls, last_result_line
        assert proc.stdout
        with transcript_path.open("a", encoding="utf-8") as transcript:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                decoded = _scrub(line.decode("utf-8", errors="replace").rstrip("\n"))
                if not decoded:
                    continue
                transcript.write(decoded + "\n")
                transcript.flush()
                try:
                    evt: Any = json.loads(decoded)
                except json.JSONDecodeError:
                    continue
                if evt.get("type") == "assistant":
                    content = evt.get("message", {}).get("content")
                    if isinstance(content, list):
                        for block in content:
                            if (
                                isinstance(block, dict)
                                and block.get("type") == "tool_use"
                                and (block.get("name") or "").endswith(
                                    "execute_python"
                                )
                            ):
                                mcp_calls += 1
                if evt.get("type") == "result":
                    last_result_line = decoded

    stderr_chunks: list[bytes] = []

    async def consume_stderr() -> None:
        assert proc.stderr
        while True:
            chunk = await proc.stderr.read(4096)
            if not chunk:
                break
            stderr_chunks.append(chunk)

    watcher = asyncio.create_task(_watch_answer(answer_path, answer_seen))
    streamers = asyncio.gather(consume_stdout(), consume_stderr())

    async def supervisor() -> None:
        await answer_seen.wait()
        # Give the CLI a short window to finish the closing transcript line.
        await asyncio.sleep(answer_grace_sec)
        if proc.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                proc.terminate()

    sup_task = asyncio.create_task(supervisor())

    try:
        if overall_timeout_sec is not None:
            await asyncio.wait_for(streamers, timeout=overall_timeout_sec)
        else:
            await streamers
        exit_code = await proc.wait()
    except asyncio.TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
        exit_code = await proc.wait()
    finally:
        watcher.cancel()
        sup_task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await watcher
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await sup_task

    duration_ms = int((time.time() - start) * 1000)

    if stderr_chunks:
        stderr_blob = _scrub(
            b"".join(stderr_chunks).decode("utf-8", errors="replace")
        )
        stderr_path.write_text(stderr_blob, encoding="utf-8")

    parsed: dict[str, Any] | None = None
    if last_result_line:
        with contextlib.suppress(json.JSONDecodeError):
            parsed = json.loads(last_result_line)
        with contextlib.suppress(OSError):
            result_path.write_text(last_result_line + "\n", encoding="utf-8")

    return ClaudeRunResult(
        exit_code=exit_code,
        duration_ms=duration_ms,
        num_turns=(parsed or {}).get("num_turns"),
        total_cost_usd=(parsed or {}).get("total_cost_usd"),
        is_error=bool((parsed or {}).get("is_error")) or exit_code != 0,
        stop_reason=(parsed or {}).get("stop_reason"),
        result_text=(parsed or {}).get("result"),
        session_id=(parsed or {}).get("session_id"),
        mcp_calls=mcp_calls,
    )


def default_prompt() -> str:
    return _DEFAULT_PROMPT


@dataclass
class AnswerFile:
    message: str
    outcome: str
    refs: list[str]


def read_answer_file(path: Path) -> AnswerFile | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    message = data.get("message") if isinstance(data.get("message"), str) else ""
    outcome = (
        data.get("outcome") if isinstance(data.get("outcome"), str) else "OUTCOME_OK"
    )
    refs_raw = data.get("refs")
    refs = (
        [r for r in refs_raw if isinstance(r, str)]
        if isinstance(refs_raw, list)
        else []
    )
    return AnswerFile(message=message, outcome=outcome, refs=refs)
