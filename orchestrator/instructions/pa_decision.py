"""Parse + validate `pa-output/pa-decision.json`, apply accepted changes.

Strict input rules:

- `mode` matches the workdir kind (`refresh` or `failure_fix`).
- `changes[]` is non-empty.
- Each entry names a `unit_id` that exists in `registry.json`.
- For `failure_fix`: `no_semantic_change` is False or absent and a
  `pa-output/units/<unit_id>/content.md` file exists.
- For `refresh`: `no_semantic_change=True` means we re-validate the
  prior content under new dep hashes; otherwise content.md is required.
- Each dependency's `(kind, path)` must resolve to a present file in
  the trial dump (fingerprint resolves to a non-None sha).
- `base_version` matches an existing version of `unit_id`.

Malformed input → `rejected.json` is written with structured reasons,
zero new versions are written, and the queue result reports
`terminal_status="rejected"`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import store, versioning
from .fingerprints import FingerprintIndex, normalize


@dataclass
class DecisionChange:
    unit_id: str
    base_version: str
    rationale: str
    rollback: str
    dependencies: list[dict[str, Any]]
    no_semantic_change: bool
    content_path: Path | None  # path to pa-output/units/<id>/content.md, or None
    content: str | None
    # Optional `conflict_resolution` block — set by PA in conflict mode
    # ({"original_base": ..., "rebased_onto": ..., "outcome": ...}).
    conflict_resolution: dict[str, Any] | None = None


@dataclass
class StaleBaseConflict:
    """One per change whose `base_version` was no longer latest at apply.

    `apply_decision` skipped writing this change; the orchestrator
    triggers a conflict retry (per `PA_CONFLICT_MODE`) that hands PA a
    fresh view of `current_latest` and asks it to rebase.
    """
    unit_id: str
    original_base: str
    current_latest: str


@dataclass
class ApplyDecisionResult:
    written: list[versioning.WrittenVersion] = field(default_factory=list)
    stale_conflicts: list[StaleBaseConflict] = field(default_factory=list)


@dataclass
class SubsumedUnit:
    """Conflict-retry decision element: PA reviewed the other PA's
    version and decided no new version is needed.

    The orchestrator does NOT create a new vNNNN/ for these — they
    only land in `report_PA.md` so the audit trail captures *why* PA
    decided to drop the change.
    """
    unit_id: str
    your_original_base: str
    current_latest: str
    rationale: str


@dataclass
class ValidatedDecision:
    mode: str
    changes: list[DecisionChange] = field(default_factory=list)
    subsumed: list[SubsumedUnit] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    stripped_world_deps: list[dict[str, Any]] = field(default_factory=list)

    @property
    def accepted(self) -> bool:
        return not self.errors


@dataclass
class NewUnitChange:
    unit_id: str
    kind: str
    render_to: str
    registry_position: str
    rationale: str
    rollback: str
    dependencies: list[dict[str, Any]]
    content_path: Path
    content: str


@dataclass
class ValidatedWorldRefreshDecision:
    baseline_version: str
    advance_baseline: bool
    changes_refresh: list[DecisionChange] = field(default_factory=list)
    changes_new: list[NewUnitChange] = field(default_factory=list)
    unchanged: list[dict[str, str]] = field(default_factory=list)
    notes_for_human: str = ""
    errors: list[dict[str, Any]] = field(default_factory=list)
    stripped_world_deps: list[dict[str, Any]] = field(default_factory=list)

    @property
    def accepted(self) -> bool:
        return not self.errors


def _err(reason: str, **fields: Any) -> dict[str, Any]:
    out = {"reason": reason}
    out.update(fields)
    return out


def validate_decision(
    *,
    project_root: Path,
    pa_dir: Path,
    expected_mode: str,
    registry_unit_ids: set[str],
    fp: FingerprintIndex,
    world_sigs: set[tuple[str, str]],
    allowed_unit_ids: set[str] | None = None,
    allow_empty_changes: bool = False,
    expected_conflict_units: set[str] | None = None,
) -> ValidatedDecision:
    """Strict-parse PA's decision file.

    `allowed_unit_ids`, when given, restricts `changes[].unit_id` further
    than the registry (e.g. a refresh job for unit X must not produce a
    new version of unit Y). When None, any registered unit is allowed —
    appropriate for failure_fix where PA picks the unit to edit.

    `allow_empty_changes` is True only for conflict-mode retries, where
    PA may legitimately decide every conflicted unit was subsumed by
    the other PA's work — i.e. no new version needed. In first-pass
    failure_fix or refresh, an empty `changes[]` is still a bug.

    `expected_conflict_units`, when given (conflict-retry only), is the
    set of units that hit a stale-base conflict. Validator enforces
    coverage: every unit in this set MUST appear in either `changes[]`
    (with `conflict_resolution`) or `subsumed[]` (with `rationale`).
    Out-of-set units in `subsumed[]` are an error.
    """
    allowed = allowed_unit_ids if allowed_unit_ids is not None else registry_unit_ids
    decision_path = pa_dir / "pa-output" / "pa-decision.json"
    if not decision_path.is_file():
        return ValidatedDecision(
            mode=expected_mode,
            errors=[_err("pa-decision.json missing", path=str(decision_path))],
        )
    try:
        raw = json.loads(decision_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return ValidatedDecision(
            mode=expected_mode,
            errors=[_err("pa-decision.json invalid json", detail=str(exc))],
        )
    if not isinstance(raw, dict):
        return ValidatedDecision(
            mode=expected_mode,
            errors=[_err("pa-decision.json is not an object")],
        )

    mode = raw.get("mode")
    errors: list[dict[str, Any]] = []
    stripped_world_deps_accum: list[dict[str, Any]] = []
    if mode != expected_mode:
        errors.append(
            _err("mode mismatch", expected=expected_mode, got=str(mode))
        )

    changes_raw = raw.get("changes")
    if not isinstance(changes_raw, list):
        errors.append(_err("changes[] missing"))
        return ValidatedDecision(mode=expected_mode, errors=errors)
    # `fix_blind` may legitimately conclude that nothing actionable is
    # visible in the trace and emit an empty `changes[]` — see prompt
    # `fix_blind.md` ("Empty changes[] is the right output …"). Other
    # modes treat an empty list as a bug.
    empty_changes_ok = allow_empty_changes or expected_mode == "fix_blind"
    if not changes_raw and not empty_changes_ok:
        errors.append(_err("changes[] empty"))
        return ValidatedDecision(mode=expected_mode, errors=errors)

    changes_out: list[DecisionChange] = []
    seen_units: set[str] = set()
    for idx, entry in enumerate(changes_raw):
        if not isinstance(entry, dict):
            errors.append(_err("changes[N] not an object", idx=idx))
            continue
        uid = entry.get("unit_id")
        base = entry.get("base_version")
        if not isinstance(uid, str) or not uid:
            errors.append(_err("unit_id missing", idx=idx))
            continue
        if uid in seen_units:
            errors.append(_err("duplicate unit_id in changes[]", idx=idx, unit_id=uid))
            continue
        seen_units.add(uid)
        if uid not in registry_unit_ids:
            errors.append(
                _err("unit_id not in registry", idx=idx, unit_id=uid)
            )
            continue
        if uid not in allowed:
            errors.append(
                _err(
                    "unit_id not allowed in this job",
                    idx=idx,
                    unit_id=uid,
                    allowed=sorted(allowed),
                )
            )
            continue
        if not isinstance(base, str) or not base:
            errors.append(_err("base_version missing", idx=idx, unit_id=uid))
            continue
        if store.get_version(project_root, uid, base) is None:
            errors.append(
                _err(
                    "base_version not found",
                    idx=idx,
                    unit_id=uid,
                    base_version=base,
                )
            )
            continue
        no_sem = bool(entry.get("no_semantic_change", False))
        if expected_mode in {"failure_fix", "fix_blind"} and no_sem:
            errors.append(
                _err(
                    "no_semantic_change not allowed in " + expected_mode,
                    unit_id=uid,
                )
            )
            continue
        deps_raw = entry.get("dependencies")
        if not isinstance(deps_raw, list):
            errors.append(_err("dependencies missing", unit_id=uid))
            continue
        dep_errors, dep_out, dep_stripped = _validate_dependencies(
            deps_raw, fp=fp, unit_id=uid, world_sigs=world_sigs
        )
        stripped_world_deps_accum.extend(dep_stripped)
        if dep_errors:
            errors.extend(dep_errors)
            continue
        rationale = (entry.get("rationale") or "").strip()
        if not rationale:
            errors.append(_err("rationale missing", unit_id=uid))
            continue
        rollback = (entry.get("rollback") or "").strip()
        if not rollback:
            errors.append(_err("rollback missing", unit_id=uid))
            continue

        content_path: Path | None = None
        content: str | None = None
        candidate = pa_dir / "pa-output" / "units" / uid / "content.md"
        if candidate.is_file():
            content_path = candidate
            try:
                content = candidate.read_text(encoding="utf-8")
            except OSError as exc:
                errors.append(
                    _err(
                        "content.md unreadable",
                        unit_id=uid,
                        path=str(candidate),
                        detail=str(exc),
                    )
                )
                continue
        else:
            if not no_sem:
                errors.append(
                    _err(
                        "content.md missing",
                        unit_id=uid,
                        expected_at=str(candidate),
                    )
                )
                continue

        conflict_block = entry.get("conflict_resolution")
        conflict_resolution: dict[str, Any] | None = None
        if conflict_block is not None:
            if not isinstance(conflict_block, dict):
                errors.append(
                    _err("conflict_resolution not an object", unit_id=uid)
                )
                continue
            outcome_val = conflict_block.get("outcome")
            if outcome_val not in ("extended", "replaced"):
                errors.append(
                    _err(
                        "conflict_resolution.outcome must be 'extended' or 'replaced' "
                        "(subsumed units must be absent from changes[])",
                        unit_id=uid,
                        outcome=str(outcome_val),
                    )
                )
                continue
            if not isinstance(conflict_block.get("original_base"), str):
                errors.append(
                    _err("conflict_resolution.original_base missing", unit_id=uid)
                )
                continue
            if not isinstance(conflict_block.get("rebased_onto"), str):
                errors.append(
                    _err("conflict_resolution.rebased_onto missing", unit_id=uid)
                )
                continue
            conflict_resolution = {
                "original_base": conflict_block["original_base"],
                "rebased_onto": conflict_block["rebased_onto"],
                "outcome": outcome_val,
            }

        changes_out.append(
            DecisionChange(
                unit_id=uid,
                base_version=base,
                rationale=rationale,
                rollback=rollback,
                dependencies=dep_out,
                no_semantic_change=no_sem,
                content_path=content_path,
                content=content,
                conflict_resolution=conflict_resolution,
            )
        )

    # ── Parse subsumed[] (conflict-retry only) + coverage check ──
    subsumed_out: list[SubsumedUnit] = []
    subsumed_raw = raw.get("subsumed")
    if subsumed_raw is not None:
        if not isinstance(subsumed_raw, list):
            errors.append(_err("subsumed[] must be a list"))
            subsumed_raw = []
        if expected_conflict_units is None and subsumed_raw:
            errors.append(_err(
                "subsumed[] only allowed in conflict-retry; current job is "
                "first-pass — remove the field"
            ))
        for sidx, sentry in enumerate(subsumed_raw):
            if not isinstance(sentry, dict):
                errors.append(_err("subsumed[N] not an object", idx=sidx))
                continue
            suid = sentry.get("unit_id")
            if not isinstance(suid, str) or not suid:
                errors.append(_err("subsumed[N].unit_id missing", idx=sidx))
                continue
            if suid not in registry_unit_ids:
                errors.append(_err(
                    "subsumed unit_id not in registry", idx=sidx, unit_id=suid
                ))
                continue
            if expected_conflict_units is not None and suid not in expected_conflict_units:
                errors.append(_err(
                    "subsumed unit was not in conflict — must not appear here",
                    idx=sidx,
                    unit_id=suid,
                    expected=sorted(expected_conflict_units),
                ))
                continue
            orig_base = sentry.get("your_original_base")
            if not isinstance(orig_base, str) or not orig_base:
                errors.append(_err(
                    "subsumed.your_original_base missing", unit_id=suid
                ))
                continue
            cur_latest = sentry.get("current_latest")
            if not isinstance(cur_latest, str) or not cur_latest:
                errors.append(_err(
                    "subsumed.current_latest missing", unit_id=suid
                ))
                continue
            rationale_s = sentry.get("rationale")
            if not isinstance(rationale_s, str) or not rationale_s.strip():
                errors.append(_err(
                    "subsumed.rationale missing — explain why no new version "
                    "is needed",
                    unit_id=suid,
                ))
                continue
            subsumed_out.append(SubsumedUnit(
                unit_id=suid,
                your_original_base=orig_base,
                current_latest=cur_latest,
                rationale=rationale_s.strip(),
            ))

    # ── Coverage check: every conflicted unit must appear in changes[] OR subsumed[] ──
    if expected_conflict_units is not None:
        covered_in_changes = {
            c.unit_id for c in changes_out
            if c.conflict_resolution is not None
        }
        covered_in_subsumed = {s.unit_id for s in subsumed_out}
        covered = covered_in_changes | covered_in_subsumed
        missing = expected_conflict_units - covered
        if missing:
            errors.append(_err(
                "conflict coverage gap: units missing from both changes[] "
                "(with conflict_resolution) and subsumed[]",
                missing=sorted(missing),
            ))
        # A unit can't be in both — split brain.
        both = covered_in_changes & covered_in_subsumed
        if both:
            errors.append(_err(
                "unit appears in both changes[] and subsumed[]",
                units=sorted(both),
            ))

    return ValidatedDecision(
        mode=expected_mode,
        changes=changes_out,
        subsumed=subsumed_out,
        errors=errors,
        stripped_world_deps=stripped_world_deps_accum,
    )


def _validate_dependencies(
    deps_raw: list[Any],
    *,
    fp: FingerprintIndex,
    unit_id: str,
    world_sigs: set[tuple[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    out: list[dict[str, Any]] = []
    stripped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for didx, d in enumerate(deps_raw):
        if not isinstance(d, dict):
            errors.append(
                _err("dependencies[N] not an object", unit_id=unit_id, idx=didx)
            )
            continue
        kind = d.get("kind")
        path = d.get("path")
        why = d.get("why")
        if kind not in store.VALID_DEP_KINDS:
            errors.append(
                _err(
                    "dependency kind invalid",
                    unit_id=unit_id,
                    idx=didx,
                    kind=str(kind),
                    allowed=list(store.VALID_DEP_KINDS),
                )
            )
            continue
        if not isinstance(path, str) or not path:
            errors.append(
                _err("dependency path missing", unit_id=unit_id, idx=didx)
            )
            continue
        if not isinstance(why, str) or not why.strip():
            errors.append(
                _err("dependency why missing", unit_id=unit_id, idx=didx)
            )
            continue
        norm_sig = (kind, normalize(kind, path))
        if norm_sig in world_sigs:
            # World-layer files are tracked separately (world_baseline +
            # world_refresh PA). Silently drop from per-unit deps; PA
            # shouldn't be loaded with the world-list membership rule.
            stripped.append(
                {"unit_id": unit_id, "kind": kind, "path": path}
            )
            continue
        sig = (kind, path)
        if sig in seen:
            errors.append(
                _err(
                    "duplicate dependency",
                    unit_id=unit_id,
                    kind=kind,
                    path=path,
                )
            )
            continue
        seen.add(sig)
        entry = fp.get(kind, path)
        if entry.sha256 is None:
            errors.append(
                _err(
                    "dependency path not present in trial dump",
                    unit_id=unit_id,
                    kind=kind,
                    path=path,
                )
            )
            continue
        record: dict[str, Any] = {
            "kind": kind,
            "path": path,
            "why": why.strip(),
        }
        if d.get("required") is False:
            record["required"] = False
        out.append(record)
    return errors, out, stripped


def write_rejected(
    *, pa_dir: Path, mode: str, validated: ValidatedDecision
) -> None:
    out = pa_dir / "pa-output" / "rejected.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "mode": mode,
                "errors": validated.errors,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


async def apply_decision(
    *,
    project_root: Path,
    validated: ValidatedDecision,
    fp: FingerprintIndex,
    trigger: dict[str, Any],
    pa_queue: Any,
    label: str = "",
) -> ApplyDecisionResult:
    """Write a new version for each accepted change, under per-unit locks.

    Stale-base check under the same lock: if `change.base_version` is no
    longer the latest active version when we reach apply (a concurrent
    PA published a newer one), we record a `StaleBaseConflict` and do
    NOT write. The caller decides whether to retry the job in
    conflict mode (`PA_CONFLICT_MODE`).

    Note on conflict-mode contract: when `change.conflict_resolution` is
    present (PA's second pass), `base_version` is expected to be the
    `current_latest` PA was told about. If that has since moved again
    (a third PA snuck in), the change is still flagged stale — the
    caller can retry up to `PA_CONFLICT_MAX_RETRIES`.
    """
    out: list[versioning.WrittenVersion] = []
    stale_conflicts: list[StaleBaseConflict] = []
    for change in validated.changes:
        lock = await pa_queue.unit_write_lock(change.unit_id)
        async with lock:
            latest_active = _latest_active_version(project_root, change.unit_id)
            if latest_active is not None and latest_active != change.base_version:
                stale_conflicts.append(
                    StaleBaseConflict(
                        unit_id=change.unit_id,
                        original_base=change.base_version,
                        current_latest=latest_active,
                    )
                )
                if label:
                    print(
                        f"{label} [PA] stale base for {change.unit_id}: "
                        f"PA used {change.base_version}, latest is {latest_active}"
                    )
                continue
            content_to_write = (
                change.content
                if change.content is not None
                else _read_base_content(project_root, change)
            )
            effective_trigger = dict(trigger)
            if change.conflict_resolution is not None:
                effective_trigger["conflict_resolution"] = change.conflict_resolution
            new = versioning.NewVersionInput(
                unit_id=change.unit_id,
                base_version=change.base_version,
                content=content_to_write,
                no_semantic_change=change.no_semantic_change,
                mode=validated.mode,
                created_by="process_architect",
                trigger=effective_trigger,
                rationale=change.rationale,
                dependencies=change.dependencies,
                rollback_note=change.rollback,
            )
            written = versioning.write_new_version(
                project_root=project_root, new=new, fp=fp
            )
            out.append(written)
            if label:
                print(
                    f"{label} [PA] wrote {written.unit_id}/{written.version} "
                    f"(deps={written.dependency_count}, "
                    f"no_sem={change.no_semantic_change})"
                )
    return ApplyDecisionResult(written=out, stale_conflicts=stale_conflicts)


def _latest_active_version(project_root: Path, unit_id: str) -> str | None:
    """Highest-numbered active version of `unit_id`, or None when there
    are no versions / all retired.
    """
    best_num = -1
    best_version: str | None = None
    for ref in store.list_versions(project_root, unit_id):
        try:
            manifest = store.load_manifest(ref)
        except Exception:
            continue
        if manifest.status != store.STATUS_ACTIVE:
            continue
        if ref.version_num > best_num:
            best_num = ref.version_num
            best_version = ref.version
    return best_version


def _read_base_content(
    project_root: Path, change: DecisionChange
) -> str:
    """Used only when PA chose no_semantic_change=True (refresh mode).

    The new version's text is identical to the parent's, but the
    dependency hashes are the current ones, so the matcher will accept
    it next trial.
    """
    ref = store.get_version(project_root, change.unit_id, change.base_version)
    if ref is None or not ref.content_path.is_file():
        return ""
    return ref.content_path.read_text(encoding="utf-8")


# ── world_refresh validation + apply ────────────────────────────────────


_UNIT_ID_RX = re.compile(r"^[a-z][a-z0-9_]*$")


def validate_world_refresh_decision(
    *,
    project_root: Path,
    pa_dir: Path,
    registry_unit_ids: set[str],
    bp_unit_ids: set[str],
    fp: FingerprintIndex,
    world_sigs: set[tuple[str, str]],
    expected_baseline_version: str,
    expected_mode: str = "world_refresh",
) -> ValidatedWorldRefreshDecision:
    """Strict-parse `pa-output/pa-decision.json` for world_refresh mode.

    Validates:
    - mode == "world_refresh"
    - baseline_version matches the workdir's expected value
    - changes_refresh entries: refresh-contract conformant
    - changes_new entries: unit_id new + valid slug, render_to unique,
      kind == business_process, content.md present, deps valid + no
      world-deps
    - registry_position: at_end | after:<id> | before:<id>
    - bp_index in changes_refresh whenever changes_new is non-empty
    - bp_index new content references each new unit's render_to
      (substring match on basename)
    - coverage: every `business_process` unit in registry appears
      exactly once across changes_refresh + changes_new + unchanged
    """
    decision_path = pa_dir / "pa-output" / "pa-decision.json"
    if not decision_path.is_file():
        return ValidatedWorldRefreshDecision(
            baseline_version=expected_baseline_version,
            advance_baseline=True,
            errors=[_err("pa-decision.json missing", path=str(decision_path))],
        )
    try:
        raw = json.loads(decision_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return ValidatedWorldRefreshDecision(
            baseline_version=expected_baseline_version,
            advance_baseline=True,
            errors=[_err("pa-decision.json invalid json", detail=str(exc))],
        )
    if not isinstance(raw, dict):
        return ValidatedWorldRefreshDecision(
            baseline_version=expected_baseline_version,
            advance_baseline=True,
            errors=[_err("pa-decision.json is not an object")],
        )

    errors: list[dict[str, Any]] = []
    mode = raw.get("mode")
    if mode != expected_mode:
        errors.append(_err("mode mismatch", expected=expected_mode, got=str(mode)))

    # `baseline_version` is no longer surfaced to PA (task-022 §6.3 dropped
    # `world-refresh-task.md`, the old carrier of this value). The
    # orchestrator already knows the baseline it queued against — use
    # `expected_baseline_version` as the source of truth. If PA volunteers
    # a value, require it to match (catch stale drafts); silence is fine.
    baseline_version = raw.get("baseline_version")
    if baseline_version is not None and baseline_version != expected_baseline_version:
        errors.append(
            _err(
                "baseline_version mismatch",
                expected=expected_baseline_version,
                got=str(baseline_version),
            )
        )

    advance_baseline = bool(raw.get("advance_baseline", True))

    changes_refresh_raw = raw.get("changes_refresh") or []
    changes_new_raw = raw.get("changes_new") or []
    unchanged_raw = raw.get("unchanged") or []
    if not isinstance(changes_refresh_raw, list):
        errors.append(_err("changes_refresh must be a list"))
        changes_refresh_raw = []
    if not isinstance(changes_new_raw, list):
        errors.append(_err("changes_new must be a list"))
        changes_new_raw = []
    if not isinstance(unchanged_raw, list):
        errors.append(_err("unchanged must be a list"))
        unchanged_raw = []

    seen_units: set[str] = set()
    changes_refresh: list[DecisionChange] = []
    stripped_world_deps_accum: list[dict[str, Any]] = []
    for idx, entry in enumerate(changes_refresh_raw):
        change, entry_errors, entry_stripped = _validate_refresh_entry(
            entry,
            idx=idx,
            pa_dir=pa_dir,
            project_root=project_root,
            registry_unit_ids=registry_unit_ids,
            fp=fp,
            world_sigs=world_sigs,
            seen_units=seen_units,
        )
        errors.extend(entry_errors)
        stripped_world_deps_accum.extend(entry_stripped)
        if change is not None:
            changes_refresh.append(change)

    existing_render_to = _registered_render_to(project_root)
    seen_new_ids: set[str] = set()
    seen_new_render: set[str] = set()
    changes_new: list[NewUnitChange] = []
    for idx, entry in enumerate(changes_new_raw):
        new_change, entry_errors, entry_stripped = _validate_new_entry(
            entry,
            idx=idx,
            pa_dir=pa_dir,
            registry_unit_ids=registry_unit_ids,
            existing_render_to=existing_render_to,
            fp=fp,
            world_sigs=world_sigs,
            seen_new_ids=seen_new_ids,
            seen_new_render=seen_new_render,
            seen_refresh_ids=seen_units,
        )
        errors.extend(entry_errors)
        stripped_world_deps_accum.extend(entry_stripped)
        if new_change is not None:
            changes_new.append(new_change)
            seen_units.add(new_change.unit_id)

    unchanged: list[dict[str, str]] = []
    for idx, entry in enumerate(unchanged_raw):
        if not isinstance(entry, dict):
            errors.append(_err("unchanged[N] not an object", idx=idx))
            continue
        uid = entry.get("unit_id")
        why = (entry.get("why") or "").strip()
        if not isinstance(uid, str) or not uid:
            errors.append(_err("unchanged[N] unit_id missing", idx=idx))
            continue
        if uid in seen_units:
            errors.append(
                _err(
                    "unit_id appears in changes_refresh/new AND unchanged",
                    idx=idx,
                    unit_id=uid,
                )
            )
            continue
        if uid not in registry_unit_ids and uid not in seen_new_ids:
            errors.append(
                _err("unchanged[N] unit_id not in registry", idx=idx, unit_id=uid)
            )
            continue
        if not why:
            errors.append(_err("unchanged[N] why missing", idx=idx, unit_id=uid))
            continue
        seen_units.add(uid)
        unchanged.append({"unit_id": uid, "why": why})

    # Coverage: every registered BP unit must appear exactly once
    # across the three lists.
    missing_coverage = bp_unit_ids - seen_units
    if missing_coverage:
        errors.append(
            _err(
                "coverage incomplete — every BP must be in changes_refresh or unchanged",
                missing=sorted(missing_coverage),
            )
        )

    # bp_index discipline: if any new units, bp_index must be in
    # changes_refresh and its new content must mention every new unit's
    # render_to basename.
    if changes_new:
        bp_index_change = next(
            (c for c in changes_refresh if c.unit_id == "bp_index"), None
        )
        if bp_index_change is None:
            errors.append(
                _err(
                    "changes_new requires bp_index in changes_refresh (new BPs need navigation)",
                    new_units=[c.unit_id for c in changes_new],
                )
            )
        elif bp_index_change.content is None:
            errors.append(
                _err(
                    "bp_index changes_refresh entry must include new content.md (cannot be no_semantic_change with changes_new)",
                )
            )
        else:
            for nc in changes_new:
                basename = nc.render_to.rsplit("/", 1)[-1]
                if basename not in bp_index_change.content:
                    errors.append(
                        _err(
                            "bp_index new content missing reference to new unit",
                            new_unit_id=nc.unit_id,
                            expected_basename=basename,
                        )
                    )

    notes = raw.get("notes_for_human")
    notes_str = notes.strip() if isinstance(notes, str) else ""

    return ValidatedWorldRefreshDecision(
        baseline_version=expected_baseline_version,
        advance_baseline=advance_baseline,
        changes_refresh=changes_refresh,
        changes_new=changes_new,
        unchanged=unchanged,
        notes_for_human=notes_str,
        errors=errors,
        stripped_world_deps=stripped_world_deps_accum,
    )


def _registered_render_to(project_root: Path) -> set[str]:
    return {u.render_to for u in store.load_registry(project_root)}


def _validate_refresh_entry(
    entry: Any,
    *,
    idx: int,
    pa_dir: Path,
    project_root: Path,
    registry_unit_ids: set[str],
    fp: FingerprintIndex,
    world_sigs: set[tuple[str, str]],
    seen_units: set[str],
) -> tuple[DecisionChange | None, list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    stripped: list[dict[str, Any]] = []
    if not isinstance(entry, dict):
        errors.append(_err("changes_refresh[N] not an object", idx=idx))
        return None, errors, stripped
    uid = entry.get("unit_id")
    base = entry.get("base_version")
    if not isinstance(uid, str) or not uid:
        errors.append(_err("unit_id missing", idx=idx))
        return None, errors, stripped
    if uid in seen_units:
        errors.append(_err("duplicate unit_id", idx=idx, unit_id=uid))
        return None, errors, stripped
    if uid not in registry_unit_ids:
        errors.append(_err("unit_id not in registry", idx=idx, unit_id=uid))
        return None, errors, stripped
    if not isinstance(base, str) or not base:
        errors.append(_err("base_version missing", idx=idx, unit_id=uid))
        return None, errors, stripped
    if store.get_version(project_root, uid, base) is None:
        errors.append(
            _err("base_version not found", idx=idx, unit_id=uid, base_version=base)
        )
        return None, errors, stripped
    no_sem = bool(entry.get("no_semantic_change", False))
    deps_raw = entry.get("dependencies")
    if not isinstance(deps_raw, list):
        errors.append(_err("dependencies missing", unit_id=uid))
        return None, errors, stripped
    dep_errors, dep_out, dep_stripped = _validate_dependencies(
        deps_raw, fp=fp, unit_id=uid, world_sigs=world_sigs
    )
    stripped.extend(dep_stripped)
    if dep_errors:
        errors.extend(dep_errors)
        return None, errors, stripped
    rationale = (entry.get("rationale") or "").strip()
    if not rationale:
        errors.append(_err("rationale missing", unit_id=uid))
        return None, errors, stripped
    rollback = (entry.get("rollback") or "").strip()
    if not rollback:
        errors.append(_err("rollback missing", unit_id=uid))
        return None, errors, stripped

    content_path: Path | None = None
    content: str | None = None
    candidate = pa_dir / "pa-output" / "units" / uid / "content.md"
    if candidate.is_file():
        content_path = candidate
        try:
            content = candidate.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(
                _err("content.md unreadable", unit_id=uid, detail=str(exc))
            )
            return None, errors, stripped
    elif not no_sem:
        errors.append(
            _err("content.md missing", unit_id=uid, expected_at=str(candidate))
        )
        return None, errors, stripped

    seen_units.add(uid)
    return (
        DecisionChange(
            unit_id=uid,
            base_version=base,
            rationale=rationale,
            rollback=rollback,
            dependencies=dep_out,
            no_semantic_change=no_sem,
            content_path=content_path,
            content=content,
        ),
        errors,
        stripped,
    )


def _validate_new_entry(
    entry: Any,
    *,
    idx: int,
    pa_dir: Path,
    registry_unit_ids: set[str],
    existing_render_to: set[str],
    fp: FingerprintIndex,
    world_sigs: set[tuple[str, str]],
    seen_new_ids: set[str],
    seen_new_render: set[str],
    seen_refresh_ids: set[str],
) -> tuple[NewUnitChange | None, list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    stripped: list[dict[str, Any]] = []
    if not isinstance(entry, dict):
        errors.append(_err("changes_new[N] not an object", idx=idx))
        return None, errors, stripped
    uid = entry.get("unit_id")
    if not isinstance(uid, str) or not uid:
        errors.append(_err("changes_new[N] unit_id missing", idx=idx))
        return None, errors, stripped
    if not _UNIT_ID_RX.match(uid):
        errors.append(
            _err(
                "changes_new[N] unit_id invalid (expect snake_case, [a-z][a-z0-9_]*)",
                idx=idx,
                unit_id=uid,
            )
        )
        return None, errors, stripped
    if uid in registry_unit_ids:
        errors.append(
            _err(
                "changes_new[N] unit_id already in registry",
                idx=idx,
                unit_id=uid,
            )
        )
        return None, errors, stripped
    if uid in seen_new_ids or uid in seen_refresh_ids:
        errors.append(_err("changes_new[N] duplicate unit_id", idx=idx, unit_id=uid))
        return None, errors, stripped
    render_to = entry.get("render_to")
    if not isinstance(render_to, str) or not render_to:
        errors.append(_err("changes_new[N] render_to missing", idx=idx, unit_id=uid))
        return None, errors, stripped
    if render_to in existing_render_to or render_to in seen_new_render:
        errors.append(
            _err(
                "changes_new[N] render_to collides with existing or another new unit",
                idx=idx,
                unit_id=uid,
                render_to=render_to,
            )
        )
        return None, errors, stripped
    kind = entry.get("kind")
    if kind != "business_process":
        errors.append(
            _err(
                "changes_new[N] kind must be 'business_process' (executor_prompt is a singleton)",
                idx=idx,
                unit_id=uid,
                kind=str(kind),
            )
        )
        return None, errors, stripped
    position = entry.get("registry_position", "at_end")
    if not isinstance(position, str) or not position:
        position = "at_end"
    if position != "at_end" and not (
        position.startswith("after:") or position.startswith("before:")
    ):
        errors.append(
            _err(
                "changes_new[N] registry_position invalid",
                idx=idx,
                unit_id=uid,
                position=position,
            )
        )
        return None, errors, stripped
    if position.startswith(("after:", "before:")):
        ref_id = position.split(":", 1)[1]
        if ref_id not in registry_unit_ids and ref_id not in seen_new_ids:
            errors.append(
                _err(
                    "changes_new[N] registry_position references unknown unit_id",
                    idx=idx,
                    unit_id=uid,
                    position=position,
                )
            )
            return None, errors, stripped

    rationale = (entry.get("rationale") or "").strip()
    if not rationale:
        errors.append(_err("changes_new[N] rationale missing", idx=idx, unit_id=uid))
        return None, errors, stripped
    rollback = (entry.get("rollback") or "").strip()
    if not rollback:
        errors.append(_err("changes_new[N] rollback missing", idx=idx, unit_id=uid))
        return None, errors, stripped

    deps_raw = entry.get("dependencies")
    if not isinstance(deps_raw, list):
        errors.append(_err("changes_new[N] dependencies missing", idx=idx, unit_id=uid))
        return None, errors, stripped
    dep_errors, dep_out, dep_stripped = _validate_dependencies(
        deps_raw, fp=fp, unit_id=uid, world_sigs=world_sigs
    )
    stripped.extend(dep_stripped)
    if dep_errors:
        errors.extend(dep_errors)
        return None, errors, stripped

    candidate = pa_dir / "pa-output" / "units" / uid / "content.md"
    if not candidate.is_file():
        errors.append(
            _err(
                "changes_new[N] content.md missing (mandatory for new units)",
                idx=idx,
                unit_id=uid,
                expected_at=str(candidate),
            )
        )
        return None, errors, stripped
    try:
        content = candidate.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(
            _err(
                "changes_new[N] content.md unreadable",
                idx=idx,
                unit_id=uid,
                detail=str(exc),
            )
        )
        return None, errors, stripped
    if not content.strip():
        errors.append(_err("changes_new[N] content.md empty", idx=idx, unit_id=uid))
        return None, errors, stripped

    seen_new_ids.add(uid)
    seen_new_render.add(render_to)
    return (
        NewUnitChange(
            unit_id=uid,
            kind=kind,
            render_to=render_to,
            registry_position=position,
            rationale=rationale,
            rollback=rollback,
            dependencies=dep_out,
            content_path=candidate,
            content=content,
        ),
        errors,
        stripped,
    )


def write_world_refresh_rejected(
    *, pa_dir: Path, validated: ValidatedWorldRefreshDecision
) -> None:
    out = pa_dir / "pa-output" / "rejected.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {"mode": "world_refresh", "errors": validated.errors}, indent=2
        )
        + "\n",
        encoding="utf-8",
    )


async def apply_world_refresh_decision(
    *,
    project_root: Path,
    validated: ValidatedWorldRefreshDecision,
    fp: FingerprintIndex,
    trigger: dict[str, Any],
    pa_queue: Any,
    world_files: list[Any],  # list[WorldFile] — typed loose to avoid cycle
    label: str = "",
    task_dir: Path | None = None,
) -> tuple[list[versioning.WrittenVersion], list[versioning.WrittenVersion], str]:
    """Apply a validated world_refresh decision atomically.

    Returns (refreshed_versions, new_unit_versions, new_baseline_version).

    Order under `pa_queue.registry_write_lock`:
    1. For each `changes_refresh[]`: per-unit lock + write new version
       (same path as failure_fix/refresh apply).
    2. For each `changes_new[]`: write v0001 of the new unit + atomically
       append to `instructions/registry.json`.
    3. Advance baseline by writing a new `world_baseline/vNNNN/` with
       current world-file bytes.

    Holding `registry_write_lock` for the full sequence guarantees that
    a concurrent failure_fix on an existing unit doesn't race the
    registry mutation, and that no two world_refresh decisions can
    interleave their registry writes.
    """
    from . import world_baseline

    refreshed: list[versioning.WrittenVersion] = []
    created_new: list[versioning.WrittenVersion] = []

    async with pa_queue.registry_write_lock:
        for change in validated.changes_refresh:
            unit_lock = await pa_queue.unit_write_lock(change.unit_id)
            async with unit_lock:
                content_to_write = (
                    change.content
                    if change.content is not None
                    else _read_base_content(project_root, change)
                )
                new = versioning.NewVersionInput(
                    unit_id=change.unit_id,
                    base_version=change.base_version,
                    content=content_to_write,
                    no_semantic_change=change.no_semantic_change,
                    mode="world_refresh",
                    created_by="process_architect",
                    trigger=trigger,
                    rationale=change.rationale,
                    dependencies=change.dependencies,
                    rollback_note=change.rollback,
                )
                written = versioning.write_new_version(
                    project_root=project_root, new=new, fp=fp
                )
                refreshed.append(written)
                if label:
                    print(
                        f"{label} [PA-wr] refreshed {written.unit_id}/{written.version}"
                    )

        for nc in validated.changes_new:
            unit_lock = await pa_queue.unit_write_lock(nc.unit_id)
            async with unit_lock:
                new = versioning.NewVersionInput(
                    unit_id=nc.unit_id,
                    base_version=None,
                    content=nc.content,
                    no_semantic_change=False,
                    mode="world_refresh",
                    created_by="process_architect",
                    trigger=trigger,
                    rationale=nc.rationale,
                    dependencies=nc.dependencies,
                    rollback_note=nc.rollback,
                )
                written = versioning.write_new_version(
                    project_root=project_root, new=new, fp=fp
                )
                created_new.append(written)
                versioning.append_registry_unit(
                    project_root=project_root,
                    unit_id=nc.unit_id,
                    kind=nc.kind,
                    render_to=nc.render_to,
                    position=nc.registry_position,
                )
                if label:
                    print(
                        f"{label} [PA-wr] new unit {written.unit_id}/{written.version} "
                        f"render_to={nc.render_to} position={nc.registry_position}"
                    )

        vault_files = (
            world_baseline._collect_task_vault(task_dir)
            if task_dir is not None
            else None
        )
        new_baseline_input = world_baseline.NewBaselineInput(
            world_files=world_files,
            fp=fp,
            created_by="process_architect",
            trigger=trigger,
            no_semantic_change=not validated.advance_baseline
            or (not validated.changes_refresh and not validated.changes_new),
            rationale=(
                "world_refresh advance from " + validated.baseline_version
            ),
            vault_files=vault_files,
        )
        new_baseline_ref = world_baseline.write_new_baseline(
            project_root=project_root, new=new_baseline_input
        )
        if label:
            print(
                f"{label} [PA-wr] advanced baseline → world_baseline/{new_baseline_ref.version}"
            )

    return refreshed, created_new, new_baseline_ref.version
