"""World layer — foundational files that shape the whole runtime.

A small set of files (declared in `agent/instructions/world.json`) is
treated as the project's "world map": when they drift, individual
business-process refreshes are wrong (one upstream change splits into N
uncoordinated per-unit jobs and misses cross-cutting domains like a
brand-new returns workflow). Instead the resolver will trigger a single
`world_refresh` PA mode that looks at the whole picture.

Public API:

- `load_world_files()` — reads `instructions/world.json`.
- `world_dep_signatures()` — `(kind, normalized_path)` set used by the
  matcher to skip world-deps and by the decision validator to forbid
  them in new manifests.
- `BaselineRef` + `list_baselines` / `get_latest_baseline` / `get_baseline`
  — read access to the immutable `instructions/world_baseline/vNNNN/`
  store.
- `compute_drift(baseline, fp, world_files)` — diff baseline manifest
  hashes against the current trial dump (or `world_files` extension
  if baseline does not list a file yet).
- `write_new_baseline(...)` — atomic writer (tmp dir + rename) used by
  the seed CLI and the `world_refresh` PA ingest path.
- `init_baseline(project_root, task_dir, ...)` — seed `v0001` from an
  existing trial dump.

`world_refresh` PA mode itself lives in `pa_workdir` and arrives in a
later step (see `.tasks/task-012/plan.md`).
"""

from __future__ import annotations

import difflib
import json
import re
import shutil
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from . import store
from .fingerprints import FingerprintIndex, normalize

WORLD_JSON_NAME = "world.json"
BASELINE_DIR_NAME = "world_baseline"
TMP_BASELINE_PREFIX = ".tmp-v"
BASELINE_VERSION_RX = re.compile(r"^v(\d{4,})$")


@dataclass(frozen=True)
class WorldFile:
    kind: str  # "workspace" | "bin_help"
    path: str
    why: str
    # When True, the file is tracked by the world layer for attention +
    # world_refresh (it still appears in `compute_drift`), but it is NOT
    # added to `world_dep_signatures` — so the per-unit matcher does not
    # skip it and the decision validator does not forbid units from
    # pinning it. Net effect: the file behaves as an ordinary per-unit
    # dependency (drift → owning unit goes stale → per-unit refresh) while
    # also surfacing in the global world-drift ATTENTION block. Used for
    # narrowly-scoped `/bin/<tool>` help files (one BP each), where the
    # fan-out the skip avoids does not apply. Cross-cutting world files
    # (`sqlite_schema.txt`, `sql.help.txt`) leave this False.
    affects_units: bool = False


def world_json_path(project_root: Path) -> Path:
    return store.instructions_dir(project_root) / WORLD_JSON_NAME


def load_world_files(project_root: Path) -> list[WorldFile]:
    fp = world_json_path(project_root)
    if not fp.is_file():
        raise FileNotFoundError(
            f"world.json missing at {fp}. The world layer is required at "
            "runtime; see .tasks/task-012/plan.md for the contract."
        )
    raw = json.loads(fp.read_text(encoding="utf-8"))
    entries = raw.get("world_files")
    if not isinstance(entries, list) or not entries:
        raise ValueError("world.json: `world_files` must be a non-empty list")
    out: list[WorldFile] = []
    seen: set[tuple[str, str]] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(f"world.json: entry not an object: {entry!r}")
        kind = entry.get("kind")
        path = entry.get("path")
        if kind not in store.VALID_DEP_KINDS:
            raise ValueError(f"world.json: invalid kind {kind!r}")
        if kind == "static":
            raise ValueError(
                "world.json: kind 'static' is not supported — world layer "
                "is about live workspace/bin-help drift, not packaged statics"
            )
        if not isinstance(path, str) or not path:
            raise ValueError(f"world.json: invalid path {path!r}")
        sig = (kind, normalize(kind, path))
        if sig in seen:
            raise ValueError(f"world.json: duplicate entry {sig}")
        seen.add(sig)
        out.append(
            WorldFile(
                kind=kind,
                path=path,
                why=str(entry.get("why", "")),
                affects_units=bool(entry.get("affects_units", False)),
            )
        )
    return out


# Auto-discovered `/bin/<tool>` help files (variant B) carry this `why`.
# affects_units stays True so the matcher still marks an owning BP stale
# (per-unit refresh) and units may legally pin the help — see
# `effective_world_files`.
AUTO_BIN_HELP_WHY = (
    "/bin tool surface (auto-tracked): every `bin-help/*.help.txt` is "
    "world-tracked so a new or changed `/bin/<tool>` surfaces in the "
    "executor world-drift ATTENTION and triggers world_refresh even when "
    "no world.json entry enumerates it. affects_units left implicitly True "
    "(absent from world_dep_signatures), so the matcher still flags an "
    "owning BP stale and a unit may pin this help as a dependency."
)


def effective_world_files(
    project_root: Path,
    fp: FingerprintIndex,
    baseline: BaselineManifest | None = None,
) -> list[WorldFile]:
    """Explicit `world.json` entries + the auto-discovered `/bin` tool surface.

    Variant B: the entire `bin-help/*.help.txt` set is world-tracked, not
    just the tools hand-listed in `world.json`. The discovery pool is the
    union of:

    - every `*.help.txt` in the live trial dump (`fp.list_bin_help()`), and
    - every `bin_help:*.help.txt` already in the latest `baseline` manifest
      (so a tool the upstream world *removed* still appears — as
      `missing_in_current` drift — instead of silently dropping out of the
      world layer the moment it disappears from the dump).

    An explicit `world.json` entry for the same path always wins: it keeps
    its curated `why` and its `affects_units` flag. That is what lets the
    cross-cutting helps stay world-only — e.g. `sql.help.txt` is listed in
    `world.json` with `affects_units: false`, so it remains matcher-skipped
    here rather than being re-derived as an auto (affects_units: true)
    per-tool help. Auto-discovered helps default to `affects_units: true`.

    Every drift / baseline-snapshot call site uses this instead of
    `load_world_files` so the resolver, the world_refresh workdir, and the
    baseline writer all agree on the same world-file set. `world.json`
    itself is never rewritten — auto helps live only in the dynamic list
    and the baseline manifest.
    """
    explicit = load_world_files(project_root)
    if baseline is None:
        # Write/seed path: snapshot only what this world actually carries.
        # An explicit `world.json` entry the upstream world removed (e.g.
        # ecom1-prod has no `/docs/README.md`, `/bin/README.md`,
        # `/run/actions/README.md`) must drop out of the new baseline —
        # exactly as an auto-discovered bin-help tool does when it leaves
        # the dump — otherwise `write_new_baseline` aborts on a file that
        # legitimately no longer exists. The read/drift path (baseline is
        # not None) keeps them so a removal still surfaces as
        # `missing_in_current` against the accepted baseline.
        explicit = [
            wf for wf in explicit if fp.get(wf.kind, wf.path).sha256 is not None
        ]
    explicit_sigs = {(wf.kind, normalize(wf.kind, wf.path)) for wf in explicit}
    discovered: set[str] = set(fp.list_bin_help())
    if baseline is not None:
        for bf in baseline.files:
            if bf.kind == "bin_help" and bf.path.endswith(".help.txt"):
                discovered.add(bf.path)
    out = list(explicit)
    for name in sorted(discovered):
        if ("bin_help", normalize("bin_help", name)) in explicit_sigs:
            continue
        out.append(
            WorldFile(
                kind="bin_help",
                path=name,
                why=AUTO_BIN_HELP_WHY,
                affects_units=True,
            )
        )
    return out


def world_dep_signatures(world_files: Iterable[WorldFile]) -> set[tuple[str, str]]:
    """`(kind, normalized_path)` set for matcher-skip / validator-forbid.

    Excludes `affects_units` world files: those stay tracked by the world
    layer for attention + world_refresh (via `compute_drift`), but must
    behave as ordinary per-unit dependencies — the matcher must NOT skip
    them and the validator must NOT forbid units from pinning them. See
    `WorldFile.affects_units` and `instructions/world.json`.
    """
    return {
        (wf.kind, normalize(wf.kind, wf.path))
        for wf in world_files
        if not wf.affects_units
    }


# ── Snapshot layout ─────────────────────────────────────────────────────


def snapshot_rel(kind: str, path: str) -> str:
    """Where inside `vNNNN/snapshot/` the bytes of a world file live.

    Schema-v2 (task-022): `workspace` lives under `snapshot/world_base/`
    so the restricted snapshot does not collide with the widened
    `vNNNN/vault/` dump that schema-v2 adds for PA consumption. Old v1
    baselines on disk used `snapshot/workspace/` and need a manual
    `mv snapshot/workspace snapshot/world_base` migration — see
    `.tasks/task-022/plan.md` §5.3.
    """
    if kind == "workspace":
        return "world_base/" + path.lstrip("/")
    if kind == "bin_help":
        return "bin-help/" + path
    raise ValueError(
        f"world snapshot does not support kind {kind!r} (static excluded "
        "from world.json by load_world_files)"
    )


# ── Baseline storage (read) ─────────────────────────────────────────────


@dataclass(frozen=True)
class BaselineFile:
    kind: str
    path: str
    sha256: str
    bytes: int

    @property
    def signature(self) -> tuple[str, str]:
        return (self.kind, normalize(self.kind, self.path))


@dataclass(frozen=True)
class BaselineManifest:
    version: str
    parent: str | None
    created_at: str
    created_by: str
    trigger: dict[str, Any]
    no_semantic_change: bool
    files: list[BaselineFile]
    raw: dict[str, Any]


@dataclass(frozen=True)
class BaselineRef:
    version: str
    version_num: int
    version_dir: Path

    @property
    def manifest_path(self) -> Path:
        return self.version_dir / "manifest.json"

    @property
    def snapshot_dir(self) -> Path:
        return self.version_dir / "snapshot"

    @property
    def diff_path(self) -> Path:
        return self.version_dir / "diff.patch"

    @property
    def changes_path(self) -> Path:
        return self.version_dir / "changes.md"

    @property
    def trigger_path(self) -> Path:
        return self.version_dir / "trigger.json"


def baseline_root_dir(project_root: Path) -> Path:
    return store.instructions_dir(project_root) / BASELINE_DIR_NAME


def list_baselines(project_root: Path) -> list[BaselineRef]:
    """Committed (`vNNNN`, not `.tmp-vNNNN`) baseline dirs, ascending."""
    root = baseline_root_dir(project_root)
    if not root.is_dir():
        return []
    refs: list[BaselineRef] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        m = BASELINE_VERSION_RX.match(child.name)
        if not m:
            continue
        refs.append(
            BaselineRef(
                version=child.name,
                version_num=int(m.group(1)),
                version_dir=child,
            )
        )
    refs.sort(key=lambda r: r.version_num)
    return refs


def get_latest_baseline(project_root: Path) -> BaselineRef | None:
    refs = list_baselines(project_root)
    return refs[-1] if refs else None


def get_baseline(project_root: Path, version: str) -> BaselineRef | None:
    for ref in list_baselines(project_root):
        if ref.version == version:
            return ref
    return None


def load_baseline_manifest(ref: BaselineRef) -> BaselineManifest:
    data = json.loads(ref.manifest_path.read_text(encoding="utf-8"))
    files_raw = data.get("files") or []
    files: list[BaselineFile] = []
    for f in files_raw:
        files.append(
            BaselineFile(
                kind=f["kind"],
                path=f["path"],
                sha256=f["sha256"],
                bytes=int(f.get("bytes", 0)),
            )
        )
    return BaselineManifest(
        version=data["version"],
        parent=data.get("parent"),
        created_at=data.get("created_at", ""),
        created_by=data.get("created_by", ""),
        trigger=data.get("trigger") or {},
        no_semantic_change=bool(data.get("no_semantic_change", False)),
        files=files,
        raw=data,
    )


def _next_baseline_num(project_root: Path) -> int:
    refs = list_baselines(project_root)
    return refs[-1].version_num + 1 if refs else 1


def _format_baseline_version(num: int) -> str:
    return f"v{num:04d}"


# ── Drift detection ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class DriftEntry:
    kind: str
    path: str
    why: str
    baseline_sha256: str | None  # None when world.json grew after baseline
    current_sha256: str | None   # None when file missing in trial dump
    status: str  # "drifted" | "missing_in_current" | "new_in_world_list"


def compute_drift(
    baseline: BaselineManifest | None,
    fp: FingerprintIndex,
    world_files: Iterable[WorldFile],
) -> list[DriftEntry]:
    """Compare each `world_files` entry to the baseline + live trial dump.

    A baseline of `None` (no v0001 seeded yet) is treated as "everything
    in `world.json` is new": every entry becomes `new_in_world_list`
    drift. Callers can use this to bootstrap baseline writes.
    """
    baseline_map: dict[tuple[str, str], BaselineFile] = {}
    if baseline is not None:
        for bf in baseline.files:
            baseline_map[bf.signature] = bf
    out: list[DriftEntry] = []
    for wf in world_files:
        sig = (wf.kind, normalize(wf.kind, wf.path))
        baseline_sha = baseline_map[sig].sha256 if sig in baseline_map else None
        entry = fp.get(wf.kind, wf.path)
        current_sha = entry.sha256
        if baseline_sha is None and current_sha is None:
            # File missing both at baseline time and now — log as missing
            # so an operator can spot a world.json typo.
            out.append(
                DriftEntry(
                    kind=wf.kind,
                    path=wf.path,
                    why=wf.why,
                    baseline_sha256=None,
                    current_sha256=None,
                    status="missing_in_current",
                )
            )
            continue
        if baseline_sha is None:
            out.append(
                DriftEntry(
                    kind=wf.kind,
                    path=wf.path,
                    why=wf.why,
                    baseline_sha256=None,
                    current_sha256=current_sha,
                    status="new_in_world_list",
                )
            )
            continue
        if current_sha is None:
            out.append(
                DriftEntry(
                    kind=wf.kind,
                    path=wf.path,
                    why=wf.why,
                    baseline_sha256=baseline_sha,
                    current_sha256=None,
                    status="missing_in_current",
                )
            )
            continue
        if current_sha != baseline_sha:
            out.append(
                DriftEntry(
                    kind=wf.kind,
                    path=wf.path,
                    why=wf.why,
                    baseline_sha256=baseline_sha,
                    current_sha256=current_sha,
                    status="drifted",
                )
            )
    return out


# ── Baseline storage (write) ────────────────────────────────────────────


@dataclass
class NewBaselineInput:
    """Inputs for a single new baseline version.

    `trigger` is caller-defined: for the seed CLI it identifies the task
    dir that supplied the bytes; for a PA-driven advance it identifies
    the world_refresh job + originating trial.

    `vault_files` (schema-v2): the widened selective dump that mirrors
    `<task_dir>/vault/` — keyed by vault-relative POSIX path (no leading
    slash, e.g. `"docs/README.md"` or `"proc/baskets/__sample__.json"`).
    When `None` or empty, the baseline does not get a `vault/` directory
    and the two new concat-diffs degrade to empty files (this is the
    case for the historical v0001/v0002 pre-schema-v2 seeds).
    """

    world_files: list[WorldFile]
    fp: FingerprintIndex
    created_by: str
    trigger: dict[str, Any]
    no_semantic_change: bool = False
    rationale: str = ""
    vault_files: dict[str, bytes] | None = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_new_baseline(
    *,
    project_root: Path,
    new: NewBaselineInput,
) -> BaselineRef:
    """Atomically write the next `world_baseline/vNNNN/`.

    Caller is responsible for serialising concurrent writes (the
    PaQueue's registry-write-lock in step 4 will own this). The CLI
    init path is single-threaded by construction.
    """
    root = baseline_root_dir(project_root)
    root.mkdir(parents=True, exist_ok=True)

    parent_ref = get_latest_baseline(project_root)
    parent_manifest = load_baseline_manifest(parent_ref) if parent_ref else None
    next_num = _next_baseline_num(project_root)
    version = _format_baseline_version(next_num)
    tmp_dir = root / f"{TMP_BASELINE_PREFIX}{version[1:]}"
    final_dir = root / version

    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)
    (tmp_dir / "snapshot").mkdir(parents=True, exist_ok=True)

    # 1. Snapshot bytes + collect manifest entries.
    files_out: list[dict[str, Any]] = []
    for wf in new.world_files:
        entry = new.fp.get(wf.kind, wf.path)
        sha = entry.sha256
        content = entry.content
        if sha is None or content is None:
            raise FileNotFoundError(
                f"world file missing at hash time: {wf.kind}:{wf.path}. "
                "Cannot seed/advance baseline against an incomplete trial "
                "dump."
            )
        snap_target = tmp_dir / "snapshot" / snapshot_rel(wf.kind, wf.path)
        snap_target.parent.mkdir(parents=True, exist_ok=True)
        snap_target.write_bytes(content)
        files_out.append(
            {
                "kind": wf.kind,
                "path": wf.path,
                "sha256": sha,
                "bytes": len(content),
                "why": wf.why,
            }
        )

    # 2. diff.patch — concatenated unified diffs vs parent baseline
    #    (over world_files-level snapshot bytes).
    diff_text = _build_baseline_diff(parent_manifest, parent_ref, new)
    (tmp_dir / "diff.patch").write_text(diff_text, encoding="utf-8")

    # 2a. vault/ — widened selective dump (schema-v2). Mirror `vault_files`
    #     verbatim into `tmp_dir/vault/<rel>`.
    if new.vault_files:
        for rel, data in sorted(new.vault_files.items()):
            target = tmp_dir / "vault" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

    # 2b. bin-help-diff.patch — one concat diff over the entire bin-help/
    #     subtree of the restricted snapshot (parent vs new).
    bin_help_diff = _build_subtree_diff(
        parent_ref=parent_ref,
        new_tmp_dir=tmp_dir,
        subdir="snapshot/bin-help",
        diff_label="bin-help",
        exclude_json=False,
    )
    (tmp_dir / "bin-help-diff.patch").write_text(bin_help_diff, encoding="utf-8")

    # 2c. vault-diff.patch — one concat diff over vault/, excluding *.json
    #     (rule-4 sample JSONs would dominate this diff otherwise).
    vault_diff = _build_subtree_diff(
        parent_ref=parent_ref,
        new_tmp_dir=tmp_dir,
        subdir="vault",
        diff_label="vault",
        exclude_json=True,
    )
    (tmp_dir / "vault-diff.patch").write_text(vault_diff, encoding="utf-8")

    # 3. manifest.json
    manifest = {
        "version": version,
        "parent": parent_ref.version if parent_ref else None,
        "created_at": _utc_now_iso(),
        "created_by": new.created_by,
        "trigger": new.trigger,
        "rationale": new.rationale,
        "no_semantic_change": new.no_semantic_change,
        "files": files_out,
    }
    (tmp_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    # 4. trigger.json — same payload as manifest.trigger, but standalone
    # so ops can `cat trigger.json` without parsing the manifest.
    (tmp_dir / "trigger.json").write_text(
        json.dumps(new.trigger, indent=2) + "\n", encoding="utf-8"
    )

    # 5. changes.md — auto-summary; PA mode can extend this in step 4.
    (tmp_dir / "changes.md").write_text(
        _build_baseline_changes_md(
            version=version,
            parent_ref=parent_ref,
            new=new,
            files_out=files_out,
            diff_text=diff_text,
        ),
        encoding="utf-8",
    )

    # 6. atomic rename.
    if final_dir.exists():
        raise FileExistsError(
            f"baseline {final_dir} already exists — write lock missing"
        )
    tmp_dir.rename(final_dir)

    return BaselineRef(
        version=version,
        version_num=next_num,
        version_dir=final_dir,
    )


def _build_baseline_diff(
    parent_manifest: BaselineManifest | None,
    parent_ref: BaselineRef | None,
    new: NewBaselineInput,
) -> str:
    """Concatenated unified diff for every file that changed vs parent.

    Empty string when there is no parent (initial seed) or nothing
    semantically changed.
    """
    if parent_manifest is None or parent_ref is None:
        return ""
    parent_by_sig: dict[tuple[str, str], BaselineFile] = {
        bf.signature: bf for bf in parent_manifest.files
    }
    chunks: list[str] = []
    for wf in new.world_files:
        sig = (wf.kind, normalize(wf.kind, wf.path))
        rel = snapshot_rel(wf.kind, wf.path)
        entry = new.fp.get(wf.kind, wf.path)
        current_bytes = entry.content or b""
        if sig in parent_by_sig:
            old_path = parent_ref.snapshot_dir / rel
            old_bytes = old_path.read_bytes() if old_path.is_file() else b""
        else:
            old_bytes = b""
        old_text = _decode(old_bytes)
        cur_text = _decode(current_bytes)
        if old_text == cur_text:
            continue
        chunks.extend(
            difflib.unified_diff(
                old_text.splitlines(keepends=True),
                cur_text.splitlines(keepends=True),
                fromfile=f"{parent_ref.version}/snapshot/{rel}",
                tofile=f"{new_baseline_label(parent_ref)}/snapshot/{rel}",
            )
        )
    return "".join(chunks)


def diff_trees(
    *,
    old_root: Path | None,
    new_root: Path | None,
    old_label: str,
    new_label: str,
    exclude_json: bool,
) -> str:
    """Concat unified-diff over the union of files under two directory roots.

    Files present only on one side diff against an empty counterpart.
    Returns `""` when neither root has any (non-excluded) files or when
    every paired file is byte-identical after the JSON filter.

    Labels become diff headers as `{label}/{rel}`; pick prefixes that
    tell the reader where each side came from (baseline vs current,
    parent vs child baseline, …).
    """

    def _collect(root: Path | None) -> dict[str, Path]:
        out: dict[str, Path] = {}
        if root is None or not root.is_dir():
            return out
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            if exclude_json and rel.lower().endswith(".json"):
                continue
            out[rel] = p
        return out

    old_files = _collect(old_root)
    new_files = _collect(new_root)
    all_rels = sorted(set(old_files) | set(new_files))
    chunks: list[str] = []
    for rel in all_rels:
        old_bytes = old_files[rel].read_bytes() if rel in old_files else b""
        new_bytes = new_files[rel].read_bytes() if rel in new_files else b""
        old_text = _decode(old_bytes)
        new_text = _decode(new_bytes)
        if old_text == new_text:
            continue
        chunks.extend(
            difflib.unified_diff(
                old_text.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile=f"{old_label}/{rel}",
                tofile=f"{new_label}/{rel}",
            )
        )
    return "".join(chunks)


# ── Relocation detection (SHA256 rename map) ────────────────────────────
#
# When the upstream world renames a directory or file, a plain tree diff
# explodes the move into a full-delete + full-add of byte-identical
# content — no continuity signal, a huge noisy patch, and a PA (or
# Executor) that has to *guess* `old → new` from prose. The organizer
# confirmed every file carries a stable SHA256, so a rename is exactly a
# `(disappeared path, appeared path)` pair whose content hash is
# unchanged. `detect_relocations` recovers that pairing; the result is
# rendered into the world_refresh workdir (`relocations.md`) and the
# Executor ATTENTION block so both can treat a move as a pure
# path-rewrite instead of a re-derivation.


def _sha256_hex(b: bytes) -> str:
    import hashlib

    return hashlib.sha256(b).hexdigest()


@dataclass(frozen=True)
class Relocation:
    """One byte-identical file that lives at a NEW path in the current world."""

    old_path: str  # root-relative POSIX path present only in the old tree
    new_path: str  # root-relative POSIX path present only in the new tree
    sha256: str
    bytes: int


@dataclass(frozen=True)
class RenamedChange:
    """A residual file with no byte-identical twin that a token-similarity pass
    judged to be the SAME document at a NEW path *and* content-edited.

    Unlike `Relocation` (byte-identical → safe pure path rewrite), this is a
    rename PLUS a content change: remap references from `old_path` to
    `new_path`, but the edited rules must be **re-derived** from the new path —
    it is NOT a silent rewrite. `similarity` is the token ratio (0..1) that
    paired them. Similarity is used here only to establish the old→new
    correspondence; it never suppresses review (content changed ⇒ always
    re-derive the affected rules).
    """

    old_path: str
    new_path: str
    similarity: float
    old_bytes: int
    new_bytes: int


@dataclass(frozen=True)
class RelocationReport:
    """SHA256-matched moves between two directory trees (old → new).

    - `relocations` — confident 1:1 moves (one disappeared path, one
      appeared path, identical content). Safe to apply as a path rename.
    - `ambiguous` — a content hash that maps to several disappeared
      and/or several appeared paths; cannot pick a single target
      mechanically, so a human/LLM must choose. Each entry is
      `{sha256, bytes, old_paths: [...], new_paths: [...]}`.
    - `renamed_changed` — a removed path and an added path with no
      byte-identical twin that a token-similarity pass paired as the same
      document, renamed AND content-edited (see `RenamedChange`). Remap the
      reference like a rename, but re-derive the changed parts.
    - `removed` — paths that vanished and whose content has no twin in
      the new tree (a genuine deletion / content rewrite, not a move).
    - `added` — paths new to the current world whose content has no twin
      in the old tree (a genuinely new artifact).

    Only paths that appear on exactly one side participate; a path present
    on both sides is an in-place edit (covered by the unified diff) and is
    never reported here.
    """

    relocations: list[Relocation]
    ambiguous: list[dict[str, Any]]
    removed: list[str]
    added: list[str]
    renamed_changed: list[RenamedChange] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.relocations or self.ambiguous)

    @property
    def has_content(self) -> bool:
        """True if ANY bucket is populated — incl. `added`/`removed`/
        `renamed_changed`.

        `is_empty` intentionally ignores added/removed (it gates the
        path-rewrite rename hint, which only byte-identical renames carry).
        `has_content` is the broader "the world's file set changed at all"
        signal used to decide whether to surface the relocation report (a
        genuinely new, removed, or renamed-and-edited file is just as worth
        flagging as a move).
        """
        return bool(
            self.relocations
            or self.ambiguous
            or self.added
            or self.removed
            or self.renamed_changed
        )


# ── Tier-2 relocation matching (rename + content edit) ─────────────────
#
# A file that was BOTH renamed AND content-edited has no byte-identical twin,
# so the SHA256 pass drops it into removed+added and the old→new continuity is
# lost — the PA then has to guess that "X disappeared" and "Y appeared" are the
# same document. We recover that pairing by *token* similarity, but only on the
# residual (hash-unmatched) removed/added sets — a handful of files — so the
# cost stays trivial and we never diff the whole tree.
#
# Similarity here ONLY establishes correspondence (so the reference can be
# remapped and the changed rules re-derived from the new path); it never
# *suppresses* review — the content changed, so affected rules are always
# re-derived. Mis-pairing is the only risk, contained by five guards: same
# parent directory, a length-ratio floor, mutual nearest-neighbour, a score
# threshold, and a runner-up margin. Below confidence a pair simply degrades to
# plain removed+added (current behaviour — strictly no worse).
#
# These four are the *defaults*; `detect_relocations(..., tau=/margin=/
# len_floor=/max_bytes=)` overrides them per call. The tuning knob for a stress
# run is `_SIM_TAU` (lower ⇒ pairs more aggressively across bigger edits, at
# more mis-pair risk). See harness-emu/README.md §"Relocation similarity".
_SIM_TAU = 0.7           # min token similarity to call two files "the same doc"
_SIM_MARGIN = 0.10       # the top match must beat the runner-up by this margin
_SIM_LEN_FLOOR = 0.5     # min(len)/max(len) — skip wildly different sizes
_SIM_MAX_BYTES = 1_000_000  # skip binary/huge files (no meaningful token diff)

# Above this token-similarity an edit (in-place or rename+edit) is "surgical" —
# the unified-diff hunk pinpoints the change and is worth inlining. Below it the
# file was effectively rewritten: the delta is a giant useless blob, so we don't
# inline it — `world-changes.md` flags it "read live" and the agent reads the
# current content. See harness-emu/README.md §"Relocation similarity".
_REWRITE_FLOOR = 0.5


def _token_similarity(a: str, b: str) -> float:
    """Token-level ratio (0..1), robust to a single changed word or text
    inserted anywhere — difflib recovers the matching blocks regardless of where
    the edit landed. autojunk off so long docs aren't silently down-weighted."""
    sm = difflib.SequenceMatcher(None, a.split(), b.split(), autojunk=False)
    return sm.ratio()


def _parent_dir(rel: str) -> str:
    i = rel.rfind("/")
    return rel[:i] if i >= 0 else ""


def detect_relocations(
    old_root: Path | None,
    new_root: Path | None,
    *,
    rel_prefix: str = "",
    tau: float = _SIM_TAU,
    margin: float = _SIM_MARGIN,
    len_floor: float = _SIM_LEN_FLOOR,
    max_bytes: int = _SIM_MAX_BYTES,
) -> RelocationReport:
    """Pair byte-identical files that moved between `old_root` and `new_root`.

    `rel_prefix` (e.g. `"vault/"` or `"bin-help/"`) is prepended to every
    reported path so a caller merging several trees keeps the paths
    globally meaningful. Trailing slash is normalised.

    `tau` / `margin` / `len_floor` / `max_bytes` tune the tier-2
    similarity pass that recovers rename+edit pairs (`renamed_changed`);
    they default to the module `_SIM_*` constants. Lower `tau` pairs more
    aggressively across bigger edits at more mis-pair risk.
    """
    prefix = rel_prefix.rstrip("/")
    if prefix:
        prefix += "/"

    def _collect(root: Path | None) -> dict[str, tuple[str, int]]:
        """rel-path → (sha256, byte-len) for every file under `root`."""
        out: dict[str, tuple[str, int]] = {}
        if root is None or not root.is_dir():
            return out
        for p in sorted(root.rglob("*")):
            if not p.is_file():
                continue
            # `__sample__.json` are our fictitious record-shape fixtures
            # (one per /proc family) — not real world content. Their
            # add/remove/move is noise, never a relocation signal, so skip
            # them on both sides (keeps relocations.md clean for PA + the
            # executor). See the proc-sample rule in agent/CLAUDE.md.
            if p.name == "__sample__.json":
                continue
            data = p.read_bytes()
            rel = prefix + p.relative_to(root).as_posix()
            out[rel] = (_sha256_hex(data), len(data))
        return out

    old = _collect(old_root)
    new = _collect(new_root)
    old_only = {rel: meta for rel, meta in old.items() if rel not in new}
    new_only = {rel: meta for rel, meta in new.items() if rel not in old}

    # Group the one-sided paths by content hash so we can pair moves.
    old_by_sha: dict[str, list[str]] = {}
    for rel, meta in old_only.items():
        old_by_sha.setdefault(meta[0], []).append(rel)
    new_by_sha: dict[str, list[str]] = {}
    for rel, meta in new_only.items():
        new_by_sha.setdefault(meta[0], []).append(rel)

    relocations: list[Relocation] = []
    ambiguous: list[dict[str, Any]] = []
    matched_old: set[str] = set()
    matched_new: set[str] = set()

    for sha in sorted(set(old_by_sha) & set(new_by_sha)):
        olds = sorted(old_by_sha[sha])
        news = sorted(new_by_sha[sha])
        matched_old.update(olds)
        matched_new.update(news)
        if len(olds) == 1 and len(news) == 1:
            nbytes = old_only[olds[0]][1]
            relocations.append(
                Relocation(
                    old_path=olds[0],
                    new_path=news[0],
                    sha256=sha,
                    bytes=nbytes,
                )
            )
        else:
            ambiguous.append(
                {
                    "sha256": sha,
                    "bytes": old_only[olds[0]][1],
                    "old_paths": olds,
                    "new_paths": news,
                }
            )

    # ── Tier 2: similarity-pair the residual removed/added (rename + edit) ──
    def _read_text(root: Path | None, rel: str) -> str | None:
        if root is None:
            return None
        sub = rel[len(prefix):] if prefix and rel.startswith(prefix) else rel
        try:
            data = (root / sub).read_bytes()
        except OSError:
            return None
        if b"\x00" in data or len(data) > max_bytes:
            return None  # binary / too large for a meaningful token diff
        return data.decode("utf-8", errors="replace")

    res_old = [rel for rel in old_only if rel not in matched_old]
    res_new = [rel for rel in new_only if rel not in matched_new]
    old_text = {rel: _read_text(old_root, rel) for rel in res_old}
    new_text = {rel: _read_text(new_root, rel) for rel in res_new}

    # similarity only within the same parent directory and within the length
    # floor — both cheap priors that kill cross-area false pairs.
    sims: dict[tuple[str, str], float] = {}
    for o in res_old:
        ot = old_text[o]
        if ot is None:
            continue
        po, lo = _parent_dir(o), old_only[o][1]
        for n in res_new:
            nt = new_text[n]
            if nt is None or _parent_dir(n) != po:
                continue
            ln = new_only[n][1]
            hi = max(lo, ln)
            if hi == 0 or min(lo, ln) / hi < len_floor:
                continue
            sims[(o, n)] = _token_similarity(ot, nt)

    # ranked candidates per side (desc score, then path) for mutual-NN + margin
    by_o: dict[str, list[tuple[float, str]]] = {}
    by_n: dict[str, list[tuple[float, str]]] = {}
    for (o, n), s in sims.items():
        by_o.setdefault(o, []).append((s, n))
        by_n.setdefault(n, []).append((s, o))
    for ranked in (*by_o.values(), *by_n.values()):
        ranked.sort(key=lambda t: (-t[0], t[1]))

    renamed_changed: list[RenamedChange] = []
    rc_old: set[str] = set()
    rc_new: set[str] = set()
    for (o, n) in sorted(sims, key=lambda k: (-sims[k], k[0], k[1])):
        s = sims[(o, n)]
        if s < tau:
            break  # sorted desc — nothing else can qualify
        if o in rc_old or n in rc_new:
            continue
        if by_o[o][0][1] != n or by_n[n][0][1] != o:
            continue  # not a mutual nearest neighbour
        o_runner = by_o[o][1][0] if len(by_o[o]) > 1 else 0.0
        n_runner = by_n[n][1][0] if len(by_n[n]) > 1 else 0.0
        if (s - o_runner) < margin or (s - n_runner) < margin:
            continue  # too close to a second candidate — leave as removed+added
        renamed_changed.append(
            RenamedChange(
                old_path=o,
                new_path=n,
                similarity=round(s, 4),
                old_bytes=old_only[o][1],
                new_bytes=new_only[n][1],
            )
        )
        rc_old.add(o)
        rc_new.add(n)

    removed = sorted(
        rel for rel in old_only if rel not in matched_old and rel not in rc_old
    )
    added = sorted(
        rel for rel in new_only if rel not in matched_new and rel not in rc_new
    )
    relocations.sort(key=lambda r: r.old_path)
    renamed_changed.sort(key=lambda r: r.old_path)
    return RelocationReport(
        relocations=relocations,
        ambiguous=ambiguous,
        removed=removed,
        added=added,
        renamed_changed=renamed_changed,
    )


def merge_relocation_reports(
    reports: Iterable[RelocationReport],
) -> RelocationReport:
    """Concatenate several reports (e.g. vault + bin-help) into one."""
    relocations: list[Relocation] = []
    ambiguous: list[dict[str, Any]] = []
    removed: list[str] = []
    added: list[str] = []
    renamed_changed: list[RenamedChange] = []
    for r in reports:
        relocations.extend(r.relocations)
        ambiguous.extend(r.ambiguous)
        removed.extend(r.removed)
        added.extend(r.added)
        renamed_changed.extend(r.renamed_changed)
    relocations.sort(key=lambda r: r.old_path)
    renamed_changed.sort(key=lambda r: r.old_path)
    return RelocationReport(
        relocations=relocations,
        ambiguous=ambiguous,
        removed=sorted(removed),
        added=sorted(added),
        renamed_changed=renamed_changed,
    )


def prune_unreferenced_added(
    report: RelocationReport,
    *,
    current_trees: Iterable[tuple[Path | None, str]],
    always_keep_basenames: tuple[str, ...] = ("AGENTS.MD", "README.md"),
) -> RelocationReport:
    """Drop `added` paths that nothing in the current world references.

    The `added` bucket otherwise force-surfaces EVERY new file as "read it live,
    source of truth" — including dated scoped-update distractor docs (e.g.
    `/docs/policy-updates/<dated>.md`) that the world documents as
    discover-by-rule, not by link. The baseline snapshot is a selective dump
    that never captures those, so they show up as `added` on every trial.

    A new file is kept only if it is **reachable**: some OTHER current-world file
    mentions its path (workspace-absolute `/docs/...` or its basename) — i.e. it
    is "derivable from README/AGENTS" and the rest of the doc graph. Index files
    themselves (`README.md` / `AGENTS.MD`) are always kept. Only `added` is
    pruned; moved/renamed/removed are genuine baseline deltas.

    `current_trees` is `[(root, rel_prefix), ...]` for the live trees (vault +
    bin-help), so a reference from any of them counts.
    """
    if not report.added:
        return report
    corpus: dict[str, str] = {}
    for root, rp in current_trees:
        if root is None or not root.is_dir():
            continue
        pfx = rp.rstrip("/")
        pfx = pfx + "/" if pfx else ""
        for p in root.rglob("*"):
            if not p.is_file() or p.name == "__sample__.json":
                continue
            try:
                corpus[pfx + p.relative_to(root).as_posix()] = _decode(p.read_bytes())
            except OSError:
                continue
    kept: list[str] = []
    for ap in report.added:
        base = ap.rsplit("/", 1)[-1]
        if base in always_keep_basenames:
            kept.append(ap)
            continue
        disp = display_path(ap)
        if any(
            (disp in text or base in text)
            for other, text in corpus.items()
            if other != ap
        ):
            kept.append(ap)
    if len(kept) == len(report.added):
        return report
    return replace(report, added=kept)


def relocations_payload(report: RelocationReport) -> dict[str, Any]:
    """JSON-able view (for `relocations.json` + `instruction-selection.json`)."""
    return {
        "relocations": [
            {
                "old_path": r.old_path,
                "new_path": r.new_path,
                "sha256": r.sha256,
                "bytes": r.bytes,
            }
            for r in report.relocations
        ],
        "ambiguous": report.ambiguous,
        "renamed_changed": [
            {
                "old_path": r.old_path,
                "new_path": r.new_path,
                "similarity": r.similarity,
                "old_bytes": r.old_bytes,
                "new_bytes": r.new_bytes,
            }
            for r in report.renamed_changed
        ],
        "removed": report.removed,
        "added": report.added,
    }


def display_path(p: str) -> str:
    """Render a relocation path the way the agent sees it live.

    `vault/`-relative paths are workspace paths read at their absolute
    `/...` location (`vault/docs/x.md` → `/docs/x.md`); `bin-help/...`
    entries (captured `/bin/<tool> --help`) stay as-is. Used by both the
    executor ATTENTION header and `relocations.md` so the same path style
    serves PA and executor.
    """
    return "/" + p[len("vault/"):] if p.startswith("vault/") else p


RELOCATIONS_TEMPLATE_NAME = "relocations.md"


def relocations_template_path(project_root: Path) -> Path:
    return store.prompts_dir(project_root) / RELOCATIONS_TEMPLATE_NAME


def render_relocations_md(report: RelocationReport, *, project_root: Path) -> str:
    """Render the audience-neutral relocations report (PA + executor share it).

    The static prose lives in `instructions/prompts/relocations.md` (editable
    without a code change); this fills its `{{MOVED}}` / `{{AMBIGUOUS}}` /
    `{{ADDED}}` / `{{REMOVED}}` placeholders with the report's buckets. Paths
    are shown via `display_path` (workspace-style `/...`), which reads
    naturally for both the executor and the PA (BP references are also
    workspace-absolute), so no audience-specific wording is needed.
    """
    template = relocations_template_path(project_root).read_text(encoding="utf-8")

    if report.relocations:
        moved_rows = [
            "| old path | read it live at | sha256 | bytes |",
            "|---|---|---|---|",
        ]
        for r in report.relocations:
            moved_rows.append(
                f"| `{display_path(r.old_path)}` | `{display_path(r.new_path)}` "
                f"| `{r.sha256[:12]}…` | {r.bytes} |"
            )
        moved = "\n".join(moved_rows)
    else:
        moved = "_(none)_"

    if report.ambiguous:
        amb_rows = []
        for a in report.ambiguous:
            olds = ", ".join(f"`{display_path(p)}`" for p in a["old_paths"])
            news = ", ".join(f"`{display_path(p)}`" for p in a["new_paths"])
            amb_rows.append(f"- sha `{a['sha256'][:12]}…`: {olds} → {news}")
        ambiguous = "\n".join(amb_rows)
    else:
        ambiguous = "_(none)_"

    if report.renamed_changed:
        rc_rows = [
            "| old path | likely now at | similarity | bytes (old→new) |",
            "|---|---|---|---|",
        ]
        for r in report.renamed_changed:
            rc_rows.append(
                f"| `{display_path(r.old_path)}` | `{display_path(r.new_path)}` "
                f"| {r.similarity:.0%} | {r.old_bytes}→{r.new_bytes} |"
            )
        renamed_changed = "\n".join(rc_rows)
    else:
        renamed_changed = "_(none)_"

    added = (
        "\n".join(f"- `{display_path(p)}`" for p in report.added)
        if report.added
        else "_(none)_"
    )
    removed = (
        "\n".join(f"- `{display_path(p)}`" for p in report.removed)
        if report.removed
        else "_(none)_"
    )

    out = (
        template.replace("{{MOVED}}", moved)
        .replace("{{AMBIGUOUS}}", ambiguous)
        .replace("{{RENAMED_CHANGED}}", renamed_changed)
        .replace("{{ADDED}}", added)
        .replace("{{REMOVED}}", removed)
    )
    return out.rstrip() + "\n"


# ── World change-set: triage index + lean edits patch ──────────────────
#
# A plain tree diff of the vault is mostly noise: every rename explodes into a
# full delete + full add of (near-)identical content, every new file is dumped
# as `+`-lines, and a full rewrite becomes a giant useless delta. The PA reads
# the whole live workspace anyway, so the diff should be an *attention
# director*, not a dump. `build_world_changes` reorganises the drift into:
#
#   - content EDITS (in-place + rename+edit) — the rule-bearing deltas. Only the
#     *surgical* ones (similarity ≥ _REWRITE_FLOOR) carry an inline hunk; a
#     rewrite is flagged "read live" instead of dumping its delta.
#   - MOVED (pure byte-identical renames), NEW, REMOVED, AMBIGUOUS — listed in
#     the manifest with "read live" pointers; never inlined.
#
# `render_world_changes_md` is the human/LLM triage index (`world-changes.md`);
# `render_world_edits_patch` is the lean patch (`world-edits.patch`) holding ONLY
# surgical hunks. Pure renames / new / removed / rewrites are excluded by design.


@dataclass(frozen=True)
class ContentEdit:
    """A file whose CONTENT changed: edited in place (`is_rename=False`,
    `old_path == new_path`) or renamed AND edited (`is_rename=True`).

    `surgical` (similarity ≥ rewrite floor) means the unified-diff `hunk` is the
    useful signal and is inlined into `world-edits.patch`; otherwise the file was
    effectively rewritten — `hunk` is empty and the reader is sent to the live
    file. Paths are display form (`/docs/...`, `bin-help/...`).
    """

    old_path: str
    new_path: str
    similarity: float
    old_bytes: int
    new_bytes: int
    is_rename: bool
    surgical: bool
    hunk: str


@dataclass(frozen=True)
class WorldChangeSet:
    """Reorganised world drift (see module note above). `moved`/`ambiguous`
    are the `RelocationReport` buckets; `added`/`removed` are display paths."""

    edits: list[ContentEdit]
    moved: list[Relocation]
    ambiguous: list[dict[str, Any]]
    added: list[str]
    removed: list[str]


def _collect_tree(root: Path | None, *, exclude_json: bool) -> dict[str, Path]:
    """rel-path → Path for every file under `root` (skips `__sample__.json`;
    optionally skips all `*.json`, matching the old vault-diff filter)."""
    out: dict[str, Path] = {}
    if root is None or not root.is_dir():
        return out
    for p in root.rglob("*"):
        if not p.is_file() or p.name == "__sample__.json":
            continue
        rel = p.relative_to(root).as_posix()
        if exclude_json and rel.lower().endswith(".json"):
            continue
        out[rel] = p
    return out


def build_world_changes(
    *,
    trees: list[tuple[Path | None, Path | None, str, bool]],
    reloc_report: RelocationReport,
    rewrite_floor: float = _REWRITE_FLOOR,
) -> WorldChangeSet:
    """Build the triage change-set from per-tree roots + the relocation report.

    `trees` is a list of `(old_root, new_root, rel_prefix, exclude_json)` — one
    per scanned subtree (e.g. vault with `exclude_json=True`, bin-help with
    `False`). `reloc_report` supplies the already-paired renames / rename+edits
    / new / removed (merged across the same trees).
    """
    prefmap: dict[str, tuple[Path | None, Path | None]] = {}
    for old_root, new_root, rp, _excl in trees:
        pfx = rp.rstrip("/")
        pfx = pfx + "/" if pfx else ""
        prefmap[pfx] = (old_root, new_root)

    def _fs(prefixed_rel: str, side: int) -> Path | None:
        for pfx, roots in prefmap.items():
            if pfx and prefixed_rel.startswith(pfx):
                sub = prefixed_rel[len(pfx):]
            elif not pfx:
                sub = prefixed_rel
            else:
                continue
            root = roots[side]
            return (root / sub) if root is not None else None
        return None

    def _hunk(old_text: str, new_text: str, frm: str, to: str) -> str:
        return "".join(
            difflib.unified_diff(
                old_text.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile=frm,
                tofile=to,
            )
        )

    edits: list[ContentEdit] = []

    # 1. in-place edits — same path on both sides, content differs.
    for old_root, new_root, rp, exclude_json in trees:
        pfx = rp.rstrip("/")
        pfx = pfx + "/" if pfx else ""
        of = _collect_tree(old_root, exclude_json=exclude_json)
        nf = _collect_tree(new_root, exclude_json=exclude_json)
        for rel in sorted(set(of) & set(nf)):
            ob = of[rel].read_bytes()
            nb = nf[rel].read_bytes()
            if ob == nb:
                continue
            ot, nt = _decode(ob), _decode(nb)
            if ot == nt:
                continue
            sim = _token_similarity(ot, nt)
            surgical = sim >= rewrite_floor
            disp = display_path(pfx + rel)
            edits.append(
                ContentEdit(
                    old_path=disp,
                    new_path=disp,
                    similarity=round(sim, 4),
                    old_bytes=len(ob),
                    new_bytes=len(nb),
                    is_rename=False,
                    surgical=surgical,
                    hunk=_hunk(ot, nt, disp, disp) if surgical else "",
                )
            )

    # 2. rename + edit — from the relocation report's similarity tier.
    for rc in reloc_report.renamed_changed:
        surgical = rc.similarity >= rewrite_floor
        hunk = ""
        if surgical:
            of, nf = _fs(rc.old_path, 0), _fs(rc.new_path, 1)
            if of and nf and of.is_file() and nf.is_file():
                hunk = _hunk(
                    _decode(of.read_bytes()),
                    _decode(nf.read_bytes()),
                    display_path(rc.old_path),
                    display_path(rc.new_path),
                )
        edits.append(
            ContentEdit(
                old_path=display_path(rc.old_path),
                new_path=display_path(rc.new_path),
                similarity=rc.similarity,
                old_bytes=rc.old_bytes,
                new_bytes=rc.new_bytes,
                is_rename=True,
                surgical=surgical,
                hunk=hunk,
            )
        )

    edits.sort(key=lambda e: (e.new_path, e.old_path))
    return WorldChangeSet(
        edits=edits,
        moved=list(reloc_report.relocations),
        ambiguous=list(reloc_report.ambiguous),
        added=[display_path(p) for p in reloc_report.added],
        removed=[display_path(p) for p in reloc_report.removed],
    )


def render_world_edits_patch(changeset: WorldChangeSet) -> str:
    """Lean patch — ONLY surgical content deltas (in-place + small rename+edit).

    Pure renames, new files, removed files, and full rewrites are excluded on
    purpose; they live in `world-changes.md` and are read live.
    """
    parts: list[str] = []
    for e in changeset.edits:
        if not e.surgical or not e.hunk:
            continue
        if e.is_rename:
            parts.append(
                f"# rename + edit: {e.old_path} -> {e.new_path} "
                f"({e.similarity:.0%} similar)\n"
            )
        parts.append(e.hunk)
        if not e.hunk.endswith("\n"):
            parts.append("\n")
    return "".join(parts)


WORLD_CHANGES_TEMPLATE_NAME = "world_changes.md"


def world_changes_template_path(project_root: Path) -> Path:
    return store.prompts_dir(project_root) / WORLD_CHANGES_TEMPLATE_NAME


def _units_cell(disp_path: str, dep_index: dict[str, list[str]]) -> str:
    """BP units that currently pin `disp_path` (full path or basename) as a
    dependency — `workspace` deps key on `/docs/...`, `bin_help` deps on the
    bare filename, so we look up both forms."""
    keys = {disp_path, disp_path.rsplit("/", 1)[-1]}
    units: set[str] = set()
    for k in keys:
        units.update(dep_index.get(k, ()))
    return ", ".join(f"`{u}`" for u in sorted(units)) if units else "—"


def render_world_changes_md(
    changeset: WorldChangeSet,
    *,
    project_root: Path,
    dep_index: dict[str, list[str]] | None = None,
) -> str:
    """Render the triage index `world-changes.md` from its template.

    `dep_index` maps a dependency path (as stored in unit manifests) to the unit
    ids that pin it; it fills the "grounds units" column. Static prose lives in
    `instructions/prompts/world_changes.md` (editable without a code change).
    """
    dep_index = dep_index or {}
    template = world_changes_template_path(project_root).read_text(encoding="utf-8")

    if changeset.edits:
        rows = ["| path | change | edit | grounds units |", "|---|---|---|---|"]
        for e in changeset.edits:
            if e.is_rename:
                path = f"`{e.old_path}` → `{e.new_path}`"
                change = "renamed + edited"
                verdict = (
                    f"surgical {e.similarity:.0%} — in patch"
                    if e.surgical
                    else f"rewritten {e.similarity:.0%} — read live at new path"
                )
            else:
                path = f"`{e.old_path}`"
                change = "edited in place"
                verdict = (
                    f"surgical {e.similarity:.0%} — in patch"
                    if e.surgical
                    else f"rewritten {e.similarity:.0%} — read live"
                )
            rows.append(
                f"| {path} | {change} | {verdict} "
                f"| {_units_cell(e.old_path, dep_index)} |"
            )
        edits = "\n".join(rows)
    else:
        edits = "_(none)_"

    if changeset.moved:
        rows = ["| old path | now at | grounds units |", "|---|---|---|"]
        for r in changeset.moved:
            op, np = display_path(r.old_path), display_path(r.new_path)
            rows.append(f"| `{op}` | `{np}` | {_units_cell(op, dep_index)} |")
        moved = "\n".join(rows)
    else:
        moved = "_(none)_"

    if changeset.added:
        rows = ["| path | grounds units |", "|---|---|"]
        rows.extend(f"| `{p}` | {_units_cell(p, dep_index)} |" for p in changeset.added)
        new = "\n".join(rows)
    else:
        new = "_(none)_"

    if changeset.removed:
        rows = ["| path | grounded units (now stale) |", "|---|---|"]
        rows.extend(f"| `{p}` | {_units_cell(p, dep_index)} |" for p in changeset.removed)
        removed = "\n".join(rows)
    else:
        removed = "_(none)_"

    if changeset.ambiguous:
        amb_rows = []
        for a in changeset.ambiguous:
            olds = ", ".join(f"`{display_path(p)}`" for p in a["old_paths"])
            news = ", ".join(f"`{display_path(p)}`" for p in a["new_paths"])
            amb_rows.append(f"- sha `{a['sha256'][:12]}…`: {olds} → {news}")
        ambiguous = "\n".join(amb_rows)
    else:
        ambiguous = "_(none)_"

    out = (
        template.replace("{{EDITS}}", edits)
        .replace("{{MOVED}}", moved)
        .replace("{{NEW}}", new)
        .replace("{{REMOVED}}", removed)
        .replace("{{AMBIGUOUS}}", ambiguous)
    )
    return out.rstrip() + "\n"


def _build_subtree_diff(
    *,
    parent_ref: BaselineRef | None,
    new_tmp_dir: Path,
    subdir: str,
    diff_label: str,
    exclude_json: bool,
) -> str:
    """Concat unified-diff over every file in `subdir/` (parent vs new).

    Used for `bin-help-diff.patch` (subdir=`snapshot/bin-help`) and
    `vault-diff.patch` (subdir=`vault`).
    """
    _ = diff_label  # reserved for future per-subtree headers
    parent_root = (parent_ref.version_dir / subdir) if parent_ref else None
    old_label = (
        f"{parent_ref.version}/{subdir}" if parent_ref else "empty"
    )
    new_label = f"{new_baseline_label(parent_ref)}/{subdir}"
    return diff_trees(
        old_root=parent_root,
        new_root=new_tmp_dir / subdir,
        old_label=old_label,
        new_label=new_label,
        exclude_json=exclude_json,
    )


def new_baseline_label(parent_ref: BaselineRef | None) -> str:
    """Best-effort label for the new baseline used in diff headers."""
    if parent_ref is None:
        return "v0001"
    return _format_baseline_version(parent_ref.version_num + 1)


def _decode(b: bytes) -> str:
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("utf-8", errors="replace")


def _build_baseline_changes_md(
    *,
    version: str,
    parent_ref: BaselineRef | None,
    new: NewBaselineInput,
    files_out: list[dict[str, Any]],
    diff_text: str,
) -> str:
    lines = [
        f"# world_baseline {version}",
        "",
        f"- created_at: `{_utc_now_iso()}`",
        f"- created_by: `{new.created_by}`",
        f"- parent: `{parent_ref.version if parent_ref else 'none'}`",
        f"- no_semantic_change: `{new.no_semantic_change}`",
    ]
    if new.rationale:
        lines.extend(["", "## Rationale", "", new.rationale.strip()])
    lines.extend(["", "## Files tracked"])
    for f in files_out:
        lines.append(
            f"- `{f['kind']}:{f['path']}` — sha256 `{f['sha256'][:12]}…`, "
            f"{f['bytes']} bytes"
        )
    if diff_text:
        lines.extend(["", "## Diff vs parent", "", "See `diff.patch`."])
    else:
        lines.extend(
            ["", "## Diff vs parent", "", "(empty — initial seed or no semantic change)"]
        )
    return "\n".join(lines) + "\n"


# ── CLI seed entry point ────────────────────────────────────────────────


def init_baseline_from_task_dir(
    *,
    project_root: Path,
    task_dir: Path,
    created_by: str = "bp_admin world-baseline init",
    rationale: str = "Manual seed from an existing trial dump.",
) -> BaselineRef:
    """Create the first baseline (`v0001`) from an existing trial dump."""
    existing = list_baselines(project_root)
    if existing:
        raise FileExistsError(
            f"world_baseline already has {len(existing)} version(s); the "
            "init path is reserved for seed. Use the world_refresh PA mode "
            "to advance baseline, or `bp_admin world-baseline rollback` to "
            "roll back (TBD)."
        )
    fp = FingerprintIndex(task_dir=task_dir, project_root=project_root)
    # Seed against the effective world-file set (explicit world.json + the
    # auto-discovered /bin tool surface) so the very first trial after a
    # seed does not spuriously drift on tools the resolver auto-tracks but
    # the baseline never snapshotted. baseline=None — this IS the seed.
    world_files = effective_world_files(project_root, fp, baseline=None)

    # Pre-flight: every world file must resolve to bytes in the task_dir.
    missing: list[str] = []
    for wf in world_files:
        entry = fp.get(wf.kind, wf.path)
        if entry.sha256 is None:
            missing.append(f"{wf.kind}:{wf.path}")
    if missing:
        raise FileNotFoundError(
            "Seed task_dir is missing world files:\n  - "
            + "\n  - ".join(missing)
            + f"\nResolved against task_dir={task_dir}. Pick a complete trial "
            "dump (vault/ + bin-help/ both populated)."
        )

    # Schema-v2: also collect the widened selective vault dump so the new
    # baseline carries everything PA needs to diff (world_refresh/world_create
    # workdirs copy `vault-diff.patch` + `bin-help-diff.patch` from here).
    vault_files = _collect_task_vault(task_dir)

    new = NewBaselineInput(
        world_files=world_files,
        fp=fp,
        created_by=created_by,
        trigger={
            "source": "manual_init",
            "task_dir": str(task_dir.resolve()),
        },
        no_semantic_change=False,
        rationale=rationale,
        vault_files=vault_files,
    )
    return write_new_baseline(project_root=project_root, new=new)


def _collect_task_vault(task_dir: Path) -> dict[str, bytes]:
    """Read every file under `task_dir/vault/` into a {rel_posix: bytes} map.

    Used by both the `bp_admin world-baseline init` CLI path and (later)
    the world_refresh PA-advance path to feed widened content into the
    new baseline's `vault/`. Returns an empty dict if `vault/` is absent
    — historical baselines tolerate an empty widened dump.
    """
    src = task_dir / "vault"
    out: dict[str, bytes] = {}
    if not src.is_dir():
        return out
    for p in src.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(src).as_posix()
        out[rel] = p.read_bytes()
    return out
