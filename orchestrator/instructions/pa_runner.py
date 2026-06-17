"""Spawn the Claude CLI inside a PA workdir.

Reused for refresh and failure_fix flows. Streams stdout to
`.logs/pa-transcript.jsonl`, accumulates stderr into
`.logs/pa-stderr.log`, and saves the final `result` line as
`pa-result.json` at the workdir root.

Stderr / transcript convention matches `claude_runner` so existing
tooling (and the Process Architect dump's CLAUDE.md notes) keeps
working unchanged.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..bootstrap import LOGS_DIR_NAME

_DUMP_MAX_FILE_BYTES = 1_000_000

PA_CLAUDE_SETTINGS = {
    "permissions": {
        "allow": [
            "Read",
            "Grep",
            "Glob",
            "Edit",
            "Write",
            # Read-only Bash allowlist for exploratory navigation. The broad
            # `Bash` deny below is the catch-all; only these specific
            # invocations are permitted.
            "Bash(find:*)",
            "Bash(ls:*)",
            "Bash(tree:*)",
            "Bash(wc:*)",
            "Bash(head:*)",
            "Bash(tail:*)",
            "Bash(diff:*)",
            "Bash(grep:*)",
            "Bash(jq:*)",
            "Bash(cat:*)",
            "Bash(sha256sum:*)",
            "Bash(stat:*)",
            "Bash(file:*)",
            "Bash(od:*)",
            "Bash(duckdb:*)",
        ],
        "deny": [
            "Bash",
            "WebFetch",
            "WebSearch",
            "mcp__ecom-python__execute_python",
            "Read(../**)",
            "Read(/etc/**)",
            "Read(/root/**)",
            "Read(~/.ssh/**)",
            "Read(~/.aws/**)",
            "Read(~/.config/**)",
            "Read(~/.claude/**)",
            "Write(../**)",
            "Write(/etc/**)",
            "Write(/root/**)",
            "Write(~/**)",
        ],
    }
}


@dataclass
class PaSpawnResult:
    exit_code: int
    duration_ms: int
    error: str | None = None
    is_error: bool = False
    api_error_status: int | None = None
    result_text: str | None = None


def write_pa_settings(pa_dir: Path) -> None:
    settings_dir = pa_dir / ".claude"
    settings_dir.mkdir(parents=True, exist_ok=True)
    (settings_dir / "settings.json").write_text(
        json.dumps(PA_CLAUDE_SETTINGS, indent=2), encoding="utf-8"
    )


def _archive_pa_attempt(pa_dir: Path, attempt_no: int) -> None:
    logs = pa_dir / LOGS_DIR_NAME
    moves = [
        (
            logs / "pa-transcript.jsonl",
            logs / f"pa-transcript-attempt-{attempt_no:02d}.jsonl",
        ),
        (
            logs / "pa-stderr.log",
            logs / f"pa-stderr-attempt-{attempt_no:02d}.log",
        ),
        (
            logs / "dump",
            logs / f"dump-attempt-{attempt_no:02d}",
        ),
        (
            pa_dir / "pa-result.json",
            logs / f"pa-result-attempt-{attempt_no:02d}.json",
        ),
    ]
    for src, dst in moves:
        if not src.exists():
            continue
        if dst.exists():
            if dst.is_dir():
                shutil.rmtree(dst)
            else:
                dst.unlink()
        shutil.move(str(src), str(dst))


def _retryable_pa_error(result: PaSpawnResult) -> str | None:
    if result.error:
        return result.error
    if result.exit_code != 0:
        return f"exit_code={result.exit_code}"
    if result.api_error_status is not None:
        return f"api_error_status={result.api_error_status}"
    text = result.result_text or ""
    if result.is_error and (
        "API Error:" in text
        or "socket connection was closed unexpectedly" in text
        or "session limit" in text
    ):
        return text
    return None


async def spawn_pa_cli(
    *,
    pa_dir: Path,
    claude_bin: str,
    model: str,
    effort: str,
    max_turns: int,
    overall_timeout_sec: float,
    user_prompt: str,
    label: str,
    internal_error_retries: int = 3,
) -> PaSpawnResult:
    max_attempts = max(0, internal_error_retries) + 1
    total_duration_ms = 0
    last_result: PaSpawnResult | None = None
    for attempt_no in range(1, max_attempts + 1):
        if attempt_no > 1:
            _archive_pa_attempt(pa_dir, attempt_no - 1)
            retry_delay = 10 * (attempt_no - 1)
            print(
                f"{label} [PA] retrying claude CLI after internal error "
                f"(attempt {attempt_no}/{max_attempts}) after "
                f"{retry_delay}s backoff"
            )
            await asyncio.sleep(retry_delay)
        result = await _spawn_pa_cli_once(
            pa_dir=pa_dir,
            claude_bin=claude_bin,
            model=model,
            effort=effort,
            max_turns=max_turns,
            overall_timeout_sec=overall_timeout_sec,
            user_prompt=user_prompt,
            label=label,
            attempt_no=attempt_no,
            max_attempts=max_attempts,
        )
        total_duration_ms += result.duration_ms
        last_result = result
        reason = _retryable_pa_error(result)
        if reason is None or attempt_no >= max_attempts:
            result.duration_ms = total_duration_ms
            return result
        print(f"{label} [PA] attempt {attempt_no}/{max_attempts} failed: {reason}")
    assert last_result is not None
    last_result.duration_ms = total_duration_ms
    return last_result


async def _spawn_pa_cli_once(
    *,
    pa_dir: Path,
    claude_bin: str,
    model: str,
    effort: str,
    max_turns: int,
    overall_timeout_sec: float,
    user_prompt: str,
    label: str,
    attempt_no: int,
    max_attempts: int,
) -> PaSpawnResult:
    logs = pa_dir / LOGS_DIR_NAME
    logs.mkdir(parents=True, exist_ok=True)
    transcript_path = logs / "pa-transcript.jsonl"
    stderr_path = logs / "pa-stderr.log"
    result_path = pa_dir / "pa-result.json"

    cli_args: list[str] = [
        "-p",
        "--output-format", "stream-json",
        "--input-format", "stream-json",
        "--verbose",
        "--permission-mode", "bypassPermissions",
        "--setting-sources", "project",
        "--disable-slash-commands",
        "--effort", effort,
        "--no-session-persistence",
        "--include-partial-messages",
        "--model", model,
    ]
    if max_turns > 0:
        cli_args.extend(["--max-turns", str(max_turns)])

    user_msg = {
        "type": "user",
        "message": {"role": "user", "content": user_prompt},
    }

    print(
        f"{label} [PA] spawning claude CLI ({model}/{effort}) "
        f"attempt {attempt_no}/{max_attempts} in {pa_dir}"
    )
    start = time.time()

    try:
        proc = await asyncio.create_subprocess_exec(
            claude_bin,
            *cli_args,
            cwd=str(pa_dir),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=10 * 1024 * 1024,
        )
    except Exception as exc:
        return PaSpawnResult(
            exit_code=-1,
            duration_ms=int((time.time() - start) * 1000),
            error=f"spawn failed: {exc!r}",
        )

    assert proc.stdin and proc.stdout and proc.stderr
    proc.stdin.write((json.dumps(user_msg) + "\n").encode("utf-8"))
    proc.stdin.close()

    last_result_line: str | None = None
    stderr_chunks: list[bytes] = []

    async def consume_stdout() -> None:
        nonlocal last_result_line
        assert proc.stdout
        with transcript_path.open("a", encoding="utf-8") as transcript:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace").rstrip("\n")
                if not decoded:
                    continue
                transcript.write(decoded + "\n")
                transcript.flush()
                with contextlib.suppress(json.JSONDecodeError):
                    obj = json.loads(decoded)
                    if isinstance(obj, dict) and obj.get("type") == "result":
                        last_result_line = decoded

    async def consume_stderr() -> None:
        assert proc.stderr
        while True:
            chunk = await proc.stderr.read(4096)
            if not chunk:
                break
            stderr_chunks.append(chunk)

    streamers = asyncio.gather(consume_stdout(), consume_stderr())
    try:
        try:
            await asyncio.wait_for(streamers, timeout=overall_timeout_sec)
            exit_code = await proc.wait()
        except asyncio.TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            exit_code = await proc.wait()
            duration_ms = int((time.time() - start) * 1000)
            if stderr_chunks:
                stderr_path.write_text(
                    b"".join(stderr_chunks).decode("utf-8", errors="replace"),
                    encoding="utf-8",
                )
            return PaSpawnResult(
                exit_code=exit_code,
                duration_ms=duration_ms,
                error="timeout",
            )

        duration_ms = int((time.time() - start) * 1000)

        if stderr_chunks:
            stderr_path.write_text(
                b"".join(stderr_chunks).decode("utf-8", errors="replace"),
                encoding="utf-8",
            )
        if last_result_line:
            with contextlib.suppress(OSError):
                result_path.write_text(last_result_line + "\n", encoding="utf-8")

        parsed_result: dict[str, Any] = {}
        if last_result_line:
            with contextlib.suppress(json.JSONDecodeError):
                obj = json.loads(last_result_line)
                if isinstance(obj, dict):
                    parsed_result = obj

        return PaSpawnResult(
            exit_code=exit_code,
            duration_ms=duration_ms,
            is_error=bool(parsed_result.get("is_error")),
            api_error_status=parsed_result.get("api_error_status"),
            result_text=parsed_result.get("result")
            if isinstance(parsed_result.get("result"), str)
            else None,
        )
    finally:
        # Always emit .logs/dump/ + augment pa-result.json — even on outer
        # cancellation (e.g. orchestrator SIGTERM). If we landed here with
        # the child still alive, kill it so the OS doesn't keep it around.
        if proc.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            with contextlib.suppress(BaseException):
                await proc.wait()
        with contextlib.suppress(Exception):
            _post_run_artifacts(pa_dir)


def assemble_claude_md(prompts_dir: Path, *, mode: str) -> str:
    """Read the mode-specific self-contained CLAUDE.md prompt for `mode`."""
    mode_file = prompts_dir / f"{mode}.md"
    if not mode_file.is_file():
        raise RuntimeError(
            f"PA prompt missing for mode={mode!r}: expected {mode_file}"
        )
    return mode_file.read_text(encoding="utf-8")


def _post_run_artifacts(pa_dir: Path) -> None:
    """Parse pa-transcript.jsonl once; emit `.logs/dump/` + augment pa-result.json.

    Best-effort: any I/O / parse failure is suppressed. Runs on both the
    timeout path and the normal completion path so a hang still leaves
    investigators a file dump.
    """
    transcript_path = pa_dir / LOGS_DIR_NAME / "pa-transcript.jsonl"
    if not transcript_path.is_file():
        return

    read_paths: set[str] = set()
    edit_paths: set[str] = set()
    write_paths: set[str] = set()
    bash_calls = 0

    try:
        text = transcript_path.read_text(encoding="utf-8")
    except OSError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict) or obj.get("type") != "assistant":
            continue
        msg = obj.get("message")
        if not isinstance(msg, dict):
            continue
        for block in msg.get("content") or []:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = block.get("name")
            inp = block.get("input")
            if not isinstance(inp, dict):
                continue
            if name == "Read":
                fp = inp.get("file_path")
                if isinstance(fp, str) and fp:
                    read_paths.add(fp)
            elif name == "Edit":
                fp = inp.get("file_path")
                if isinstance(fp, str) and fp:
                    edit_paths.add(fp)
            elif name == "Write":
                fp = inp.get("file_path")
                if isinstance(fp, str) and fp:
                    write_paths.add(fp)
            elif name == "Bash":
                bash_calls += 1

    _emit_dump(pa_dir, paths=read_paths | edit_paths | write_paths)
    _augment_pa_result(
        pa_dir,
        read_paths=read_paths,
        edit_paths=edit_paths,
        write_paths=write_paths,
        bash_calls=bash_calls,
    )


def _emit_dump(pa_dir: Path, *, paths: set[str]) -> None:
    """Copy every file PA Read/Edit/Wrote into `.logs/dump/<rel>` (final state)."""
    if not paths:
        return
    dump_root = pa_dir / LOGS_DIR_NAME / "dump"
    try:
        pa_dir_abs = pa_dir.resolve()
    except OSError:
        return
    dump_rel_prefix = f"{LOGS_DIR_NAME}/dump"
    for fp_str in sorted(paths):
        src = Path(fp_str)
        if not src.is_absolute():
            src = pa_dir / fp_str
        try:
            src_abs = src.resolve()
        except OSError:
            continue
        try:
            rel = src_abs.relative_to(pa_dir_abs)
        except ValueError:
            # Outside the workdir — `Read(../**)` deny should prevent this,
            # but skip defensively if a path slips through.
            continue
        rel_str = str(rel)
        if rel_str.startswith(dump_rel_prefix):
            continue
        if not src_abs.is_file():
            continue
        try:
            if src_abs.stat().st_size > _DUMP_MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        target = dump_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(OSError):
            shutil.copyfile(src_abs, target)


def _augment_pa_result(
    pa_dir: Path,
    *,
    read_paths: set[str],
    edit_paths: set[str],
    write_paths: set[str],
    bash_calls: int,
) -> None:
    """Add a `pa_aggregate` block with counters to pa-result.json."""
    result_path = pa_dir / "pa-result.json"
    if not result_path.is_file():
        return
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(result, dict):
        return

    deps_declared = 0
    decision_path = pa_dir / "pa-output" / "pa-decision.json"
    if decision_path.is_file():
        try:
            decision = json.loads(decision_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            decision = None
        if isinstance(decision, dict):
            for change in decision.get("changes") or []:
                if isinstance(change, dict):
                    deps = change.get("dependencies") or []
                    if isinstance(deps, list):
                        deps_declared += len(deps)

    vh_reads = sum(1 for p in read_paths if "/version-history/" in p)

    result["pa_aggregate"] = {
        "files_read": len(read_paths),
        "files_under_version_history_read": vh_reads,
        "files_edited": len(edit_paths),
        "files_written": len(write_paths),
        "bash_calls": bash_calls,
        "deps_declared": deps_declared,
    }

    with contextlib.suppress(OSError):
        result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")
