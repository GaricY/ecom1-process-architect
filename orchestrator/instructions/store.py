"""Filesystem layout helpers + manifest parsing for the instruction store.

The store lives at `<project_root>/instructions/`:

- `registry.json` — flat list of units the resolver must materialise.
- `units/<unit_id>/v0001/` — first version of one unit; deterministic
  Python is the only thing that writes new `vNNNN` directories.
- `prompts/process_architect/*.md` — non-versioned PA prompt fragments.

Each version directory holds five artifacts:

- `content.md` — the prose the executor reads (or PA reads for context).
- `manifest.json` — parent / status / dependencies / rationale.
- `changes.md` — human-readable "why this version exists".
- `diff.patch` — unified diff of `content.md` against parent (or empty).
- `dependency_snapshot/` — old contents of every declared dependency, so
  future stale diffs can compare old-vs-current.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

VERSION_RX = re.compile(r"^v(\d{4,})$")
TMP_VERSION_PREFIX = ".tmp-v"
STATUS_ACTIVE = "active"
STATUS_RETIRED = "retired"
VALID_DEP_KINDS = ("workspace", "bin_help", "static", "sql_table")


@dataclass(frozen=True)
class RegistryUnit:
    id: str
    kind: str  # "executor_prompt" | "business_process"
    render_to: str


@dataclass(frozen=True)
class Dependency:
    kind: str
    path: str
    sha256: str | None
    why: str
    required: bool


@dataclass(frozen=True)
class Manifest:
    unit_id: str
    version: str
    parent: str | None
    status: str
    created_at: str
    created_by: str
    mode: str
    trigger: dict[str, Any]
    rationale: str
    dependencies: list[Dependency]
    rollback: dict[str, Any]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VersionRef:
    unit_id: str
    version: str
    version_num: int
    version_dir: Path

    @property
    def manifest_path(self) -> Path:
        return self.version_dir / "manifest.json"

    @property
    def content_path(self) -> Path:
        return self.version_dir / "content.md"

    @property
    def snapshot_dir(self) -> Path:
        return self.version_dir / "dependency_snapshot"

    @property
    def changes_path(self) -> Path:
        return self.version_dir / "changes.md"

    @property
    def diff_path(self) -> Path:
        return self.version_dir / "diff.patch"


def instructions_dir(project_root: Path) -> Path:
    return project_root / "instructions"


def registry_path(project_root: Path) -> Path:
    return instructions_dir(project_root) / "registry.json"


def units_dir(project_root: Path) -> Path:
    return instructions_dir(project_root) / "units"


def unit_dir(project_root: Path, unit_id: str) -> Path:
    return units_dir(project_root) / unit_id


def prompts_dir(project_root: Path) -> Path:
    return instructions_dir(project_root) / "prompts"


def pa_prompts_dir(project_root: Path) -> Path:
    return prompts_dir(project_root) / "process_architect"


def pa_user_prompt_path(project_root: Path, mode: str) -> Path:
    return pa_prompts_dir(project_root) / f"{mode}_user.md"


def load_registry(project_root: Path) -> list[RegistryUnit]:
    rp = registry_path(project_root)
    if not rp.is_file():
        raise FileNotFoundError(
            f"instruction store missing at {rp}. The versioned instruction "
            "store lives under `agent/instructions/` (registry.json + "
            "units/<id>/vNNNN/...). It is required at runtime and must be "
            "committed alongside `orchestrator/instructions/` Python code."
        )
    raw = json.loads(rp.read_text(encoding="utf-8"))
    out: list[RegistryUnit] = []
    seen: set[str] = set()
    for entry in raw.get("units") or []:
        uid = entry["id"]
        if uid in seen:
            raise ValueError(f"registry.json: duplicate unit id {uid!r}")
        seen.add(uid)
        out.append(
            RegistryUnit(
                id=uid,
                kind=entry["kind"],
                render_to=entry["render_to"],
            )
        )
    return out


def preflight_instruction_store(project_root: Path) -> None:
    """Validate `agent/instructions/` before the orchestrator starts trials.

    Fails fast with a clear, operator-actionable error when the store is
    missing pieces, so we don't burn an external `start_run` or a fresh
    `pre_bootstrap_dump` only to crash inside the resolver.
    """
    registry = load_registry(project_root)
    problems: list[str] = []
    # Local import: world_baseline imports store, so importing at module
    # level would deadlock the circular dependency.
    from . import world_baseline
    try:
        world_baseline.load_world_files(project_root)
    except (FileNotFoundError, ValueError) as exc:
        problems.append(f"world.json: {exc}")
    pa_dir = pa_prompts_dir(project_root)
    for fname in (
        "refresh.md",
        "refresh_user.md",
        "failure_fix.md",
        "failure_fix_user.md",
        "fix_blind.md",
        "fix_blind_user.md",
        "world_refresh.md",
        "world_refresh_user.md",
        "world_create.md",
        "world_create_user.md",
        "conflict.md",
        "conflict_user.md",
        "bp_author_contract.md",
    ):
        if not (pa_dir / fname).is_file():
            problems.append(f"missing PA prompt fragment: {pa_dir / fname}")
    for unit in registry:
        udir = unit_dir(project_root, unit.id)
        if not udir.is_dir():
            problems.append(
                f"unit {unit.id!r}: no directory at {udir}"
            )
            continue
        versions = list_versions(project_root, unit.id)
        if not versions:
            problems.append(f"unit {unit.id!r}: no `vNNNN/` versions found")
            continue
        active = [
            v
            for v in versions
            if load_manifest(v).status == STATUS_ACTIVE
        ]
        if not active:
            problems.append(
                f"unit {unit.id!r}: all versions are retired — "
                "create a new active version via bp_admin rollback"
            )
    if problems:
        details = "\n".join(f"  - {p}" for p in problems)
        raise FileNotFoundError(
            "instruction store preflight failed:\n" + details
        )


def list_versions(project_root: Path, unit_id: str) -> list[VersionRef]:
    """Return committed (`vNNNN`, not `.tmp-vNNNN`) version dirs, ascending."""
    udir = unit_dir(project_root, unit_id)
    if not udir.is_dir():
        return []
    refs: list[VersionRef] = []
    for child in udir.iterdir():
        if not child.is_dir():
            continue
        m = VERSION_RX.match(child.name)
        if not m:
            continue
        refs.append(
            VersionRef(
                unit_id=unit_id,
                version=child.name,
                version_num=int(m.group(1)),
                version_dir=child,
            )
        )
    refs.sort(key=lambda r: r.version_num)
    return refs


def get_version(project_root: Path, unit_id: str, version: str) -> VersionRef | None:
    for ref in list_versions(project_root, unit_id):
        if ref.version == version:
            return ref
    return None


def load_manifest(ref: VersionRef) -> Manifest:
    data = json.loads(ref.manifest_path.read_text(encoding="utf-8"))
    deps_raw = data.get("dependencies") or []
    deps: list[Dependency] = []
    for d in deps_raw:
        kind = d["kind"]
        if kind not in VALID_DEP_KINDS:
            raise ValueError(
                f"{ref.unit_id}/{ref.version}: invalid dependency kind {kind!r}"
            )
        deps.append(
            Dependency(
                kind=kind,
                path=d["path"],
                sha256=d.get("sha256"),
                why=d.get("why", ""),
                required=bool(d.get("required", True)),
            )
        )
    return Manifest(
        unit_id=data["unit_id"],
        version=data["version"],
        parent=data.get("parent"),
        status=data.get("status", STATUS_ACTIVE),
        created_at=data.get("created_at", ""),
        created_by=data.get("created_by", ""),
        mode=data.get("mode", ""),
        trigger=data.get("trigger") or {},
        rationale=data.get("rationale", ""),
        dependencies=deps,
        rollback=data.get("rollback") or {},
        raw=data,
    )


def next_version_num(project_root: Path, unit_id: str) -> int:
    refs = list_versions(project_root, unit_id)
    return refs[-1].version_num + 1 if refs else 1


def format_version(num: int) -> str:
    return f"v{num:04d}"
