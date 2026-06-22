"""Compute sha256 fingerprints of live source files for the matcher.

The resolver compares each version manifest's declared dependency
hashes against the current trial dump. The mapping from
`(kind, path)` to a local file is the only thing that ties an
abstract dependency declaration to bytes on disk:

- `workspace:/AGENTS.MD`   → `<task_dir>/vault/AGENTS.MD`
- `workspace:/docs/security.md` → `<task_dir>/vault/docs/security.md`
- `bin_help:payments/recover.help.txt` → `<task_dir>/bin-help/payments/recover.help.txt`
- `static:static-instructions/workspace.py` → `<project_root>/static-instructions/workspace.py`
- `sql_table:payments` → the `TABLE payments` block in
  `<task_dir>/bin-help/sqlite_schema.txt`

Files that resolve to a missing path produce `sha256=None`; the
matcher reports those as `actual_state=missing` in the stale report.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FingerprintKey:
    kind: str
    path: str  # normalised


@dataclass(frozen=True)
class FingerprintEntry:
    key: FingerprintKey
    local_path: Path | None
    sha256: str | None
    content: bytes | None


def normalize(kind: str, path: str) -> str:
    if kind == "workspace":
        return path if path.startswith("/") else "/" + path
    if kind == "sql_table":
        return path.strip().lower()
    return path


def fingerprint_key(kind: str, path: str) -> FingerprintKey:
    return FingerprintKey(kind=kind, path=normalize(kind, path))


class FingerprintIndex:
    """Lazy cache of (kind, path) → FingerprintEntry for one task_dir."""

    def __init__(self, *, task_dir: Path, project_root: Path) -> None:
        self._task_dir = task_dir
        self._project_root = project_root
        self._cache: dict[FingerprintKey, FingerprintEntry] = {}

    def get(self, kind: str, path: str) -> FingerprintEntry:
        key = fingerprint_key(kind, path)
        if key in self._cache:
            return self._cache[key]
        if key.kind == "sql_table":
            entry = self._get_sql_table(key)
            self._cache[key] = entry
            return entry
        local = self._resolve_local(key)
        if local is None or not local.is_file():
            entry = FingerprintEntry(
                key=key, local_path=local, sha256=None, content=None
            )
        else:
            content = local.read_bytes()
            entry = FingerprintEntry(
                key=key,
                local_path=local,
                sha256=hashlib.sha256(content).hexdigest(),
                content=content,
            )
        self._cache[key] = entry
        return entry

    def list_bin_help(self) -> list[str]:
        """Every `*.help.txt` under `<task_dir>/bin-help/`, as bin_help paths.

        Used by the world layer to treat the whole `/bin` tool surface as
        world-tracked without enumerating each tool in `world.json` (so a
        brand-new or mutated `/bin/<tool>` always surfaces in the executor
        world-drift ATTENTION and triggers `world_refresh`). Returns
        bin_help-relative POSIX paths (e.g. `reserve.help.txt` or
        `payments/recover.help.txt`), sorted. Excludes `sqlite_schema.txt`
        (not a tool `--help`; it is tracked explicitly in `world.json`).
        """
        root = self._task_dir / "bin-help"
        if not root.is_dir():
            return []
        out: list[str] = []
        for p in sorted(root.rglob("*.help.txt")):
            if p.is_file():
                out.append(p.relative_to(root).as_posix())
        return out

    def _get_sql_table(self, key: FingerprintKey) -> FingerprintEntry:
        schema_path = self._task_dir / "bin-help" / "sqlite_schema.txt"
        if not schema_path.is_file():
            return FingerprintEntry(
                key=key, local_path=schema_path, sha256=None, content=None
            )
        schema_text = schema_path.read_text(encoding="utf-8", errors="replace")
        table = re.escape(key.path)
        # A table block is its `TABLE <name>` header plus the following
        # 2-space-indented column lines (and any blank lines between them).
        # Match greedily and let the block end at the first line that is
        # neither — the next `TABLE`, the trailing `## Enumerations …`
        # appendix, or EOF. An earlier `(?=^TABLE |\Z)` lookahead only
        # recognised the first and last of those, so the *last* table
        # before the appendix never matched and was reported absent.
        match = re.search(
            rf"(?m)^TABLE {table}(?: [^\n]*)?\n(?:(?:  [^\n]*)?\n)*",
            schema_text,
        )
        if not match:
            return FingerprintEntry(
                key=key, local_path=schema_path, sha256=None, content=None
            )
        content = match.group(0).rstrip().encode("utf-8") + b"\n"
        return FingerprintEntry(
            key=key,
            local_path=schema_path,
            sha256=hashlib.sha256(content).hexdigest(),
            content=content,
        )

    def _resolve_local(self, key: FingerprintKey) -> Path | None:
        if key.kind == "workspace":
            rel = key.path.lstrip("/")
            if not rel:
                return None
            return self._task_dir / "vault" / rel
        if key.kind == "bin_help":
            return self._task_dir / "bin-help" / key.path
        if key.kind == "static":
            return self._project_root / key.path
        if key.kind == "sql_table":
            return self._task_dir / "bin-help" / "sqlite_schema.txt"
        return None
