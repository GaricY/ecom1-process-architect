"""Render a human/agent-readable digest of one Executor session.

After `run_claude_cli` returns, the trial directory contains:

- `.logs/python/execute_NNNN.{py,stdout,stderr}` — every snippet the agent ran.
- `.logs/mcp-tool-calls.jsonl` — every inner `ws.*` call, with snippet-start
  markers inserted by `python_executor.execute_python`.
- `scratchpad.json`, `state.json`, `answer.json` — final state (at task_dir root).
- `.logs/transcript.jsonl` — the raw stream-json Claude transcript (huge).

`write_executor_actions` walks all of that and writes a single
`.logs/executor_actions.md` digest. The Process Architect agent reads this
digest (not the raw transcript) when it analyses a failed trial — it is the
single source of "what did the executor do".
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .bootstrap import LOGS_DIR_NAME

SNIPPET_RX = re.compile(r"^execute_(\d+)\.py$")
MAX_SNIPPET_STREAM_BYTES = 8000
MAX_TOOL_CALL_BODY_BYTES = 600


@dataclass
class SnippetRecord:
    idx: int
    snippet: str
    code: str
    stdout: str
    stderr: str
    tool_calls: list[dict[str, Any]]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return ""


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _collect_snippets(python_dir: Path) -> list[tuple[int, Path]]:
    """Return [(idx, snippet_path)] sorted by idx."""
    out: list[tuple[int, Path]] = []
    if not python_dir.is_dir():
        return out
    for entry in python_dir.iterdir():
        if not entry.is_file():
            continue
        m = SNIPPET_RX.match(entry.name)
        if not m:
            continue
        out.append((int(m.group(1)), entry))
    out.sort(key=lambda t: t[0])
    return out


def _group_tool_calls(rows: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    """Group tool-call rows by snippet idx using `_marker` boundaries."""
    out: dict[int, list[dict[str, Any]]] = {}
    current_idx = -1
    for row in rows:
        if row.get("_marker") == "snippet_start":
            current_idx = int(row.get("idx") or -1)
            out.setdefault(current_idx, [])
            continue
        if current_idx < 0:
            out.setdefault(0, []).append(row)
        else:
            out[current_idx].append(row)
    return out


def _strip_prelude(code: str) -> str:
    """Trim the auto-prepended `exec(open(runtime_prelude.py)...)` header."""
    marker = "# --- agent code below ---\n"
    if marker in code:
        return code.split(marker, 1)[1]
    return code


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 16] + "\n…[truncated]\n"


def _render_tool_call_one(row: dict[str, Any]) -> str:
    """Compact single-line description of one inner tool call."""
    tool = str(row.get("tool", "?"))
    if tool == "exec":
        path = row.get("path", "")
        args = row.get("args") or []
        if path == "/bin/sql":
            stdin_bytes = row.get("stdin_bytes")
            return f"sql ({stdin_bytes}B)"
        return f"exec {path} {' '.join(map(str, args))}".rstrip()
    if tool in {"read", "stat", "list", "find", "search", "tree"}:
        keys = [
            f"{k}={row[k]!r}"
            for k in ("path", "root", "name", "pattern", "level", "limit")
            if k in row
        ]
        return f"{tool} {' '.join(keys)}".rstrip()
    if tool == "write":
        return f"write {row.get('path', '')} ({row.get('bytes', 0)}B)"
    if tool == "delete":
        return f"delete {row.get('path', '')}"
    if tool == "answer":
        return (
            f"answer outcome={row.get('outcome', '')} "
            f"refs={row.get('refs', [])}"
        )
    return f"{tool} {json.dumps({k: v for k, v in row.items() if k != 'tool'})[:MAX_TOOL_CALL_BODY_BYTES]}"


def _format_snippet(rec: SnippetRecord) -> list[str]:
    code = _strip_prelude(rec.code).rstrip()
    out = [
        f"### Snippet {rec.idx} — `.logs/python/{rec.snippet}`",
        "",
        "```python",
        code or "(empty)",
        "```",
        "",
    ]
    if rec.tool_calls:
        out.append("**Inner tool calls** (in order):")
        for row in rec.tool_calls:
            out.append(f"- `{_render_tool_call_one(row)}`")
        out.append("")
    stdout = rec.stdout.strip()
    stderr = rec.stderr.strip()
    if stdout:
        out.append("**stdout:**")
        out.append("```")
        out.append(_truncate(stdout, MAX_SNIPPET_STREAM_BYTES).rstrip())
        out.append("```")
        out.append("")
    if stderr:
        out.append("**stderr:**")
        out.append("```")
        out.append(_truncate(stderr, MAX_SNIPPET_STREAM_BYTES).rstrip())
        out.append("```")
        out.append("")
    if not stdout and not stderr:
        out.append("_(no stdout / stderr)_")
        out.append("")
    return out


def build_executor_actions(
    *,
    task_dir: Path,
    task_id: str,
    trial_id: str,
    instruction: str,
    score: float | None,
    score_detail: list[str],
    answer_outcome: str,
) -> str:
    """Compose the markdown for `.logs/executor_actions.md`."""
    logs_dir = task_dir / LOGS_DIR_NAME
    python_dir = logs_dir / "python"
    tool_calls_path = logs_dir / "mcp-tool-calls.jsonl"
    # Working docs / final answer remain at task_dir root.
    scratchpad_path = task_dir / "scratchpad.json"
    state_path = task_dir / "state.json"
    answer_path = task_dir / "answer.json"

    snippet_files = _collect_snippets(python_dir)
    grouped = _group_tool_calls(_load_jsonl(tool_calls_path))

    records: list[SnippetRecord] = []
    for idx, snippet_path in snippet_files:
        rec = SnippetRecord(
            idx=idx,
            snippet=snippet_path.name,
            code=_read_text(snippet_path),
            stdout=_read_text(python_dir / f"execute_{idx:04d}.stdout"),
            stderr=_read_text(python_dir / f"execute_{idx:04d}.stderr"),
            tool_calls=grouped.get(idx, []),
        )
        records.append(rec)

    score_str = "N/A" if score is None else f"{score * 100:.1f}%"
    passed = (score == 1.0)
    status = "PASS" if passed else ("FAIL" if score is not None else "UNKNOWN")

    scratchpad = _read_text(scratchpad_path).strip() or "{}"
    state = _read_text(state_path).strip() or "{}"
    answer = _read_text(answer_path).strip() or "(no answer.json)"

    lines: list[str] = [
        f"# Executor actions — {task_id} ({trial_id})",
        "",
        f"- **status:** {status}",
        f"- **score:** {score_str}",
        f"- **answer_outcome:** {answer_outcome}",
        f"- **snippets:** {len(records)}",
        f"- **inner tool calls:** {sum(len(r.tool_calls) for r in records)}",
        "",
        "## Task instruction",
        "",
        "```",
        instruction.strip(),
        "```",
        "",
    ]
    if score_detail:
        lines.extend(
            [
                "## Score detail (from get_trial)",
                "",
                *[f"- {item}" for item in score_detail],
                "",
            ]
        )
    lines.extend(
        [
            "## Final answer (answer.json)",
            "",
            "```json",
            answer,
            "```",
            "",
            "## Snippet timeline",
            "",
        ]
    )
    for rec in records:
        lines.extend(_format_snippet(rec))
    lines.extend(
        [
            "## Final scratchpad",
            "",
            "```json",
            scratchpad,
            "```",
            "",
            "## Final state",
            "",
            "```json",
            state,
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def write_executor_actions(
    *,
    task_dir: Path,
    task_id: str,
    trial_id: str,
    instruction: str,
    score: float | None,
    score_detail: list[str],
    answer_outcome: str,
) -> Path:
    text = build_executor_actions(
        task_dir=task_dir,
        task_id=task_id,
        trial_id=trial_id,
        instruction=instruction,
        score=score,
        score_detail=score_detail,
        answer_outcome=answer_outcome,
    )
    logs_dir = task_dir / LOGS_DIR_NAME
    logs_dir.mkdir(parents=True, exist_ok=True)
    out_path = logs_dir / "executor_actions.md"
    out_path.write_text(text, encoding="utf-8")
    return out_path
