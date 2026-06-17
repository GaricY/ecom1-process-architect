"""Atomic writer for new version directories.

A new version dir contains five things, all generated deterministically
by Python (never by the PA LLM):

- `content.md`        — PA-supplied text (or copied parent text on a
                        revalidation-only "no semantic change" refresh).
- `manifest.json`     — version metadata + hashed dependency list.
- `changes.md`        — short human note (PA rationale + dep diff
                        pointers).
- `diff.patch`        — unified diff of `content.md` against the
                        parent's `content.md` (empty if parent=None).
- `dependency_snapshot/` — exact bytes of every declared dependency
                        captured at this version's hashing time.

We write everything under `.tmp-vNNNN/`, then `rename(.tmp-vNNNN, vNNNN)`
in a single syscall so the resolver never sees a half-written version
directory. The unit-level write lock (held by `pa_queue`) prevents two
PA jobs from picking the same `vNNNN`.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import store
from .fingerprints import FingerprintIndex


@dataclass
class NewVersionInput:
    unit_id: str
    base_version: str | None
    content: str
    no_semantic_change: bool
    mode: str  # "refresh" | "failure_fix" | "rollback" | "initial_migration"
    created_by: str
    trigger: dict[str, Any]
    rationale: str
    dependencies: list[dict[str, Any]]  # [{kind, path, why, required?}]
    rollback_note: str


@dataclass
class WrittenVersion:
    unit_id: str
    version: str
    version_dir: Path
    dependency_count: int


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_new_version(
    *,
    project_root: Path,
    new: NewVersionInput,
    fp: FingerprintIndex,
) -> WrittenVersion:
    """Build a brand-new `vNNNN/` dir under `units/<unit_id>/`.

    Caller MUST hold the unit's write lock around this function so the
    allocated version number stays consistent.
    """
    unit_dir = store.unit_dir(project_root, new.unit_id)
    unit_dir.mkdir(parents=True, exist_ok=True)

    next_num = store.next_version_num(project_root, new.unit_id)
    version = store.format_version(next_num)
    tmp_dir = unit_dir / f"{store.TMP_VERSION_PREFIX}{version[1:]}"
    final_dir = unit_dir / version

    # Wipe leftover from a crashed prior attempt before re-allocating.
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)
    (tmp_dir / "dependency_snapshot").mkdir(parents=True, exist_ok=True)

    # 1. content.md — verbatim PA text.
    (tmp_dir / "content.md").write_text(new.content, encoding="utf-8")

    # 2. diff.patch — old (parent) vs new content.
    parent_ref: store.VersionRef | None = None
    parent_content = ""
    if new.base_version:
        parent_ref = store.get_version(project_root, new.unit_id, new.base_version)
        if parent_ref is not None and parent_ref.content_path.is_file():
            parent_content = parent_ref.content_path.read_text(encoding="utf-8")
    diff_lines = list(
        difflib.unified_diff(
            parent_content.splitlines(keepends=True),
            new.content.splitlines(keepends=True),
            fromfile=f"{new.unit_id}/{new.base_version or 'none'}/content.md",
            tofile=f"{new.unit_id}/{version}/content.md",
        )
    )
    (tmp_dir / "diff.patch").write_text("".join(diff_lines), encoding="utf-8")

    # 3. dependencies — hash + snapshot each.
    hashed_deps: list[dict[str, Any]] = []
    for dep in new.dependencies:
        entry = fp.get(dep["kind"], dep["path"])
        sha = entry.sha256
        if sha is None and dep.get("required", True):
            # Snapshot the absence by writing an empty file in the snapshot
            # tree — caller (decision validator) is responsible for catching
            # this before reaching us, but be defensive.
            sha = hashlib.sha256(b"").hexdigest()
        record: dict[str, Any] = {
            "kind": dep["kind"],
            "path": dep["path"],
            "sha256": sha,
            "why": dep.get("why", ""),
        }
        if dep.get("required") is False:
            record["required"] = False
        hashed_deps.append(record)
        # Save snapshot bytes (or empty file for missing).
        snap_rel = _snapshot_rel(dep["kind"], dep["path"])
        snap_target = tmp_dir / "dependency_snapshot" / snap_rel
        snap_target.parent.mkdir(parents=True, exist_ok=True)
        snap_target.write_bytes(entry.content or b"")

    # 4. manifest.json.
    manifest = {
        "unit_id": new.unit_id,
        "version": version,
        "parent": new.base_version,
        "status": store.STATUS_ACTIVE,
        "created_at": utc_now_iso(),
        "created_by": new.created_by,
        "mode": new.mode,
        "trigger": new.trigger,
        "rationale": new.rationale,
        "dependencies": hashed_deps,
        "rollback": {"strategy": new.rollback_note}
        if new.rollback_note
        else {},
        "no_semantic_change": new.no_semantic_change,
    }
    (tmp_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    # 5. changes.md.
    chg_lines: list[str] = [
        f"# {new.unit_id} {version}",
        "",
        f"- mode: `{new.mode}`",
        f"- created_by: `{new.created_by}`",
        f"- created_at: `{manifest['created_at']}`",
    ]
    if new.base_version:
        chg_lines.append(f"- parent: `{new.base_version}`")
    if new.no_semantic_change:
        chg_lines.append(
            "- no_semantic_change: revalidated against the new "
            "dependency hashes without text edits"
        )
    chg_lines.extend(["", "## Rationale", "", new.rationale.strip() or "(none)"])
    if new.rollback_note:
        chg_lines.extend(["", "## Rollback", "", new.rollback_note.strip()])
    if hashed_deps:
        chg_lines.extend(["", "## Dependencies"])
        for dep in hashed_deps:
            chg_lines.append(
                f"- `{dep['kind']}:{dep['path']}` — {dep.get('why', '').strip() or '(no why)'}"
            )
    (tmp_dir / "changes.md").write_text("\n".join(chg_lines) + "\n", encoding="utf-8")

    # 6. Atomic rename. Final dir must not already exist (write lock prevents).
    if final_dir.exists():
        raise FileExistsError(
            f"version {final_dir} already exists — write lock did not serialise"
        )
    tmp_dir.rename(final_dir)

    return WrittenVersion(
        unit_id=new.unit_id,
        version=version,
        version_dir=final_dir,
        dependency_count=len(hashed_deps),
    )


def _snapshot_rel(kind: str, path: str) -> str:
    """Where inside dependency_snapshot/ the bytes get stored."""
    if kind == "workspace":
        return "workspace/" + path.lstrip("/")
    if kind == "bin_help":
        return "bin-help/" + path
    if kind == "static":
        return "static/" + path
    if kind == "sql_table":
        return "sql-table/" + path.strip().lower() + ".schema.txt"
    raise ValueError(f"unknown dependency kind {kind!r}")


def append_registry_unit(
    *,
    project_root: Path,
    unit_id: str,
    kind: str,
    render_to: str,
    position: str,
) -> None:
    """Atomically append a new unit entry to `instructions/registry.json`.

    `position` is one of:
    - `"at_end"` (default)
    - `"after:<existing_unit_id>"`
    - `"before:<existing_unit_id>"`

    Caller MUST hold `PaQueue.registry_write_lock` so two concurrent
    `world_refresh` decisions can never write a half-merged registry.
    The write itself is atomic via tmp file + rename.

    Validates: `unit_id` not already present; if `after:`/`before:` the
    referenced id exists; `kind` non-empty; `render_to` not colliding
    with any existing `render_to`.
    """
    registry_path = store.registry_path(project_root)
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    units = data.get("units")
    if not isinstance(units, list):
        raise ValueError(
            f"registry.json malformed (units not a list): {registry_path}"
        )

    existing_ids = {u.get("id") for u in units if isinstance(u, dict)}
    existing_render = {u.get("render_to") for u in units if isinstance(u, dict)}
    if unit_id in existing_ids:
        raise ValueError(f"unit_id {unit_id!r} already in registry")
    if render_to in existing_render:
        raise ValueError(
            f"render_to {render_to!r} collides with an existing unit"
        )
    if not kind:
        raise ValueError("kind must be non-empty")

    new_entry: dict[str, Any] = {
        "id": unit_id,
        "kind": kind,
        "render_to": render_to,
    }

    if position == "at_end":
        units.append(new_entry)
    elif position.startswith("after:"):
        ref_id = position.split(":", 1)[1]
        idx = _find_unit_index(units, ref_id)
        units.insert(idx + 1, new_entry)
    elif position.startswith("before:"):
        ref_id = position.split(":", 1)[1]
        idx = _find_unit_index(units, ref_id)
        units.insert(idx, new_entry)
    else:
        raise ValueError(
            f"position must be 'at_end' | 'after:<id>' | 'before:<id>', "
            f"got {position!r}"
        )

    data["units"] = units
    tmp_path = registry_path.with_suffix(registry_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(registry_path)


def _find_unit_index(units: list[Any], unit_id: str) -> int:
    for i, u in enumerate(units):
        if isinstance(u, dict) and u.get("id") == unit_id:
            return i
    raise ValueError(f"position references unknown unit_id {unit_id!r}")


def retire_version(
    *,
    project_root: Path,
    unit_id: str,
    version: str,
    reason: str,
) -> None:
    """Flip `status` to `retired` in a version's manifest.

    The artifact itself is preserved on disk so a future trial whose
    fingerprints happen to match retired-only versions can fail-fast
    with a clear "RETIRED_ONLY" status instead of silently picking a
    bad version.
    """
    ref = store.get_version(project_root, unit_id, version)
    if ref is None:
        raise FileNotFoundError(f"no such version: {unit_id}/{version}")
    data = json.loads(ref.manifest_path.read_text(encoding="utf-8"))
    data["status"] = store.STATUS_RETIRED
    data["retired_at"] = utc_now_iso()
    data["retired_reason"] = reason
    ref.manifest_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
