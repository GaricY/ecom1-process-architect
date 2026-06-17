"""Match versions, fall back on stale, render into task_dir.

Public entry point: `resolve_and_render` is called from
`task_dir.materialize` after `pre_bootstrap_dump` + `build_bin_help`
have populated `vault/` and `bin-help/`.

Matching is purely deterministic: for each unit in `registry.json`,
walk versions newest-first and pick the first whose required
dependencies all hash to the current trial dump. If none match, fall
back to the latest active version and flag it `stale_latest_fallback`.

The stale handler then applies `STALE_RESOLUTION`:

- `latest_async_refresh` — render the stale fallback into the task dir
  immediately, queue a PA refresh job at `async_refresh` priority, do
  not wait.
- `wait_for_refresh` — queue the same job at `blocking_refresh` priority,
  await its result, re-run the matcher, render the (possibly fresh)
  selection.

Both modes always start the executor; failed PA jobs render the latest
fallback with a `stale_refresh_failed` / `stale_refresh_incomplete`
warning rather than blocking the trial.

Fatal errors (unit with no versions, all retired, or registry pointing
at an unknown unit) raise before the executor starts — those represent
human-only operational problems, not stale runtime state.
"""

from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import store, world_baseline
from .fingerprints import FingerprintIndex, normalize

LOGS_DIR_NAME = ".logs"
ATTENTION_DIR_NAME = "attention"
ATTENTION_BP_FILENAME = "CLAUDE.md"

# Per-unit selection_status values.
MATCHED = "matched"
STALE_LATEST_FALLBACK = "stale_latest_fallback"
STALE_REFRESH_FAILED = "stale_refresh_failed"
STALE_REFRESH_INCOMPLETE = "stale_refresh_incomplete"
NO_VERSIONS = "no_versions"
RETIRED_ONLY = "retired_only"

# Top-level SelectionResult.status values.
MATCHED_AFTER_REFRESH = "matched_after_refresh"

STALE_RESOLUTION_LATEST_ASYNC = "latest_async_refresh"
STALE_RESOLUTION_WAIT = "wait_for_refresh"
VALID_STALE_RESOLUTIONS = (
    STALE_RESOLUTION_LATEST_ASYNC,
    STALE_RESOLUTION_WAIT,
)


@dataclass
class UnitSelection:
    unit_id: str
    kind: str
    render_to: str
    selected_version: str | None
    selection_status: str
    mismatches: list[dict[str, Any]] = field(default_factory=list)
    matched_dependencies: int = 0


@dataclass
class SelectionResult:
    status: str
    stale_resolution: str
    units: list[UnitSelection]
    executor_started: bool
    pa_refresh: dict[str, Any] | None
    world_refresh: dict[str, Any] | None = None
    world_drift: list[dict[str, Any]] | None = None
    attention: dict[str, Any] | None = None
    fatal_errors: list[str] = field(default_factory=list)


def _matches(
    manifest: store.Manifest,
    fp: FingerprintIndex,
    world_sigs: set[tuple[str, str]],
) -> tuple[bool, list[dict[str, Any]]]:
    mismatches: list[dict[str, Any]] = []
    for dep in manifest.dependencies:
        if not dep.required:
            continue
        if (dep.kind, normalize(dep.kind, dep.path)) in world_sigs:
            # World-layer files are handled by the world_refresh PA mode,
            # not by per-unit refresh. The matcher silently ignores them
            # so an upstream change to e.g. `/AGENTS.MD` does not trigger
            # N parallel per-unit jobs. Note: world files flagged
            # `affects_units` in world.json are deliberately absent from
            # `world_sigs` (see world_dep_signatures), so they fall through
            # and DO mark the owning unit stale — they still surface in the
            # world-drift ATTENTION via compute_drift, which reads the full
            # world_files list independently of world_sigs.
            continue
        entry = fp.get(dep.kind, dep.path)
        if entry.sha256 != dep.sha256:
            mismatches.append(
                {
                    "kind": dep.kind,
                    "path": dep.path,
                    "expected_sha256": dep.sha256,
                    "actual_sha256": entry.sha256,
                    "actual_state": "missing" if entry.sha256 is None else "present",
                    "why": dep.why,
                }
            )
    return len(mismatches) == 0, mismatches


def _has_real_deps(manifest: store.Manifest) -> bool:
    return any(d.required for d in manifest.dependencies)


def _select_one(
    project_root: Path,
    unit_id: str,
    fp: FingerprintIndex,
    world_sigs: set[tuple[str, str]],
) -> tuple[store.VersionRef | None, str, store.Manifest | None, list[dict[str, Any]]]:
    refs = store.list_versions(project_root, unit_id)
    if not refs:
        return None, NO_VERSIONS, None, []

    active: list[tuple[store.VersionRef, store.Manifest]] = []
    for ref in refs:
        try:
            manifest = store.load_manifest(ref)
        except Exception as exc:
            # A malformed manifest is treated as inert; the version is
            # skipped. Surface it via stderr so an operator can spot it.
            print(f"warn: cannot parse manifest for {ref.version_dir}: {exc}")
            continue
        if manifest.status == store.STATUS_ACTIVE:
            active.append((ref, manifest))

    if not active:
        return None, RETIRED_ONLY, None, []

    # Newest-first scan, but never let an older empty-deps "always-match"
    # version shadow a newer real-deps version that turned stale — that
    # would defeat the refresh path. An empty-deps version is only
    # eligible when it is the latest active version (initial migration
    # state).
    active_desc = sorted(active, key=lambda x: x[0].version_num, reverse=True)
    latest_ref, latest_manifest = active_desc[0]
    for ref, manifest in active_desc:
        is_latest = ref is latest_ref
        if not is_latest and not _has_real_deps(manifest):
            continue
        ok, mismatches = _matches(manifest, fp, world_sigs)
        if ok:
            return ref, MATCHED, manifest, []
    _, mismatches = _matches(latest_manifest, fp, world_sigs)
    return latest_ref, STALE_LATEST_FALLBACK, latest_manifest, mismatches


def _stale_warning(unit_id: str, mismatches: list[dict[str, Any]]) -> str:
    """Per-BP header prepended to a stale unit's rendered content.

    Scoped to a single BP: lists only the deps that drifted for THIS
    unit plus a link to each corresponding diff under `attention/`. The
    executor sees this header only on BPs that actually went stale, so
    unrelated BPs are not told to second-guess themselves. World-layer
    drift gets the broader CLAUDE.md ATTENTION block instead.
    """
    lines = [
        "> **Heads-up — this process may be out of date.**",
        ">",
        (
            "> Files this process was drafted against have changed. "
            "Skim the diff(s) below before applying — the description "
            "may quote sentences that no longer exist, or omit ones "
            "that now do."
        ),
        ">",
    ]
    if mismatches:
        lines.append("> Changed dependencies:")
        for m in mismatches:
            rel = _snapshot_rel(m["kind"], m["path"])
            slug = rel.replace("/", "_")
            lines.append(
                f"> - `{m['path']}` — "
                f"[diff](../{ATTENTION_DIR_NAME}/unit-diffs/{unit_id}/{slug}.patch)"
            )
    else:
        lines.append("> Changed dependencies: (none specifically flagged)")
    lines.extend(
        [
            ">",
            (
                "> When the description below disagrees with what you "
                "read live via `execute_python`, **trust the live read**."
            ),
            "",
        ]
    )
    return "\n".join(lines)


_PLACEHOLDER_RX = re.compile(r"\{\{([A-Z_][A-Z0-9_]*)\}\}")
_PLACEHOLDER_LINE_RX = re.compile(
    r"(?m)^(?P<indent>[ \t]*)(?P<lead>.*)\{\{(?P<name>[A-Z_][A-Z0-9_]*)\}\}(?P<tail>.*)$"
)

# A BP `content.md` ends with a `## Dependencies` section — an authoring /
# audit-trail convention the resolver's matcher uses to detect stale upstream
# files. The Executor never needs it, so we cut it (always the last `##`
# section) before rendering into the task dir. Non-BP units (executor_core,
# bp_index) have no such section, so this is a no-op for them.
_DEPENDENCIES_RX = re.compile(r"(?m)^##[ \t]+Dependencies[ \t]*$")


def _strip_dependencies(content: str) -> str:
    m = _DEPENDENCIES_RX.search(content)
    if m is None:
        return content
    return content[: m.start()].rstrip() + "\n"


def _apply_placeholders(content: str, substitutions: dict[str, str]) -> str:
    """Substitute `{{NAME}}` tokens and fail loud on any leftover.

    Bootstrap-time replacement of trial-static values (identity, sim-date)
    into the rendered prompt. Multi-line values inherit the leading
    indentation of the placeholder line so they sit cleanly inside an
    indented markdown code fence. We refuse to write a prompt that still
    contains an unresolved `{{...}}` — a typo in content.md or a new
    placeholder nobody wired up should crash the trial, not silently leak
    into the agent's context.
    """

    def _sub(match: re.Match[str]) -> str:
        name = match.group("name")
        if name not in substitutions:
            # Leave intact; the leftover check below will surface it.
            return match.group(0)
        indent = match.group("indent")
        lead = match.group("lead")
        tail = match.group("tail")
        value = substitutions[name]
        value_lines = value.split("\n")
        rendered = [indent + lead + value_lines[0]]
        for extra in value_lines[1:]:
            rendered.append(indent + extra if extra else extra)
        rendered[-1] = rendered[-1] + tail
        return "\n".join(rendered)

    content = _PLACEHOLDER_LINE_RX.sub(_sub, content)
    leftover = _PLACEHOLDER_RX.findall(content)
    if leftover:
        raise ValueError(
            "unresolved instruction placeholders: "
            + ", ".join(sorted(set(leftover)))
            + f"; known: {sorted(substitutions)}"
        )
    return content


def _render_static_bp_attention(task_dir: Path, substitutions: dict[str, str]) -> None:
    """Substitute trial-static placeholders into `business_processes/CLAUDE.md`.

    That file is copied verbatim from `static-instructions/` by bootstrap, so
    — unlike every versioned unit — it never passes through `_render_unit`,
    and its `{{TRIAL_IDENTITY}}` / `{{TRIAL_DATE}}` tokens would otherwise
    leak literally. Claude Code auto-loads this CLAUDE.md whenever the
    executor reads a BP file, so surfacing the pre-rendered `/bin/id` /
    `/bin/date` here spares a turn for the many BPs that key on identity or
    sim-date.

    Run once before any world-drift ATTENTION header is prepended (see
    `_write_executor_attention`) so that header is never placeholder-scanned.
    Reuses `_apply_placeholders` including its fail-loud leftover check: a
    typo'd `{{...}}` in the static file crashes the trial instead of reaching
    the agent.
    """
    bp_claude = task_dir / "business_processes" / ATTENTION_BP_FILENAME
    if not bp_claude.is_file():
        return
    original = bp_claude.read_text(encoding="utf-8")
    rendered = _apply_placeholders(original, substitutions)
    if rendered != original:
        bp_claude.write_text(rendered, encoding="utf-8")


def _render_unit(
    *,
    sel: UnitSelection,
    ref: store.VersionRef,
    task_dir: Path,
    is_stale: bool,
    substitutions: dict[str, str],
) -> None:
    target = task_dir / sel.render_to
    target.parent.mkdir(parents=True, exist_ok=True)
    content = ref.content_path.read_text(encoding="utf-8")
    content = _apply_placeholders(content, substitutions)
    content = _strip_dependencies(content)
    if is_stale:
        # The stale header is advisory — the BP body is still usable
        # without it. If header construction blows up (e.g. unexpected
        # mismatch shape), surface a warning and render the BP plain so
        # the trial can still start. Killing bootstrap here would turn
        # every advisory bug into a guaranteed task failure.
        try:
            warning = _stale_warning(sel.unit_id, sel.mismatches)
        except Exception as exc:
            print(
                f"warn: _stale_warning failed for {sel.unit_id}: {exc!r}; "
                "rendering BP without stale header"
            )
            warning = ""
        if warning:
            content = warning + "\n" + content
    target.write_text(content, encoding="utf-8")


def _logs_dir(task_dir: Path) -> Path:
    p = task_dir / LOGS_DIR_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def _snapshot_rel(kind: str, path: str) -> str:
    """Where a dep's bytes live under `vNNNN/dependency_snapshot/` or the
    world baseline `snapshot/`. Mirrors versioning._snapshot_rel."""
    if kind == "workspace":
        return "workspace/" + path.lstrip("/")
    if kind == "bin_help":
        return "bin-help/" + path
    if kind == "static":
        return "static/" + path
    if kind == "sql_table":
        return "sql-table/" + path.strip().lower() + ".schema.txt"
    raise ValueError(f"unknown dependency kind {kind!r}")


def _decode(b: bytes) -> str:
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("utf-8", errors="replace")


def _diff_lines(
    *,
    old_bytes: bytes,
    new_bytes: bytes,
    fromfile: str,
    tofile: str,
) -> str:
    old_text = _decode(old_bytes)
    new_text = _decode(new_bytes)
    if old_text == new_text:
        return ""
    return "".join(
        difflib.unified_diff(
            old_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=fromfile,
            tofile=tofile,
        )
    )


# Match references inside backticks that look like workspace paths or
# tool invocations. Restricted to the prefixes we actually use in this
# repo (`/docs`, `/run`, `/bin`, `/proc`, `/var`, `/tmp`, `/AGENTS.MD`)
# so prose-y backtick'd words like `LIKE` or `LOWER(col)` don't leak in.
_REF_INSIDE_BACKTICKS_RX = re.compile(
    r"`("
    r"/AGENTS\.MD"
    r"|/(?:docs|run|bin|proc|var|tmp)"
    r"(?:/[A-Za-z0-9._-]+)*"
    r"(?:\s+[a-z][a-z0-9-]+)?"   # optional /bin/<tool> <subcommand>
    r")`"
)


def _collect_paths(text: str) -> set[str]:
    """All backtick'd workspace-ish refs in `text` (no dedup over lines)."""
    return {m.group(1) for m in _REF_INSIDE_BACKTICKS_RX.finditer(text)}


def _extract_new_refs(patch_text: str) -> list[dict[str, str]]:
    """Find truly-new references introduced by added lines in a unified diff.

    "Truly-new" means the reference appears in at least one added line
    AND does not appear in any removed-or-context line within the same
    patch. This filters out refs that were only re-quoted by a rewording
    and surfaces the genuinely new artifacts (new policy file, new tool
    subcommand) the Executor should sniff.

    Returns a list of `{path, sample}` dicts, where `sample` is the
    first added line that mentions the ref (truncated). Order is the
    order of first appearance, so callers can render a stable list.
    """
    baseline_refs: set[str] = set()
    added_refs: dict[str, str] = {}  # path → first sample line
    for line in patch_text.splitlines():
        if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
            continue
        if line.startswith("+"):
            body = line[1:]
            for ref in _collect_paths(body):
                added_refs.setdefault(ref, body.strip())
        elif line.startswith("-") or line.startswith(" "):
            body = line[1:] if line.startswith(("-", " ")) else line
            baseline_refs.update(_collect_paths(body))
    out: list[dict[str, str]] = []
    for path, sample in added_refs.items():
        if path in baseline_refs:
            continue
        # Trim sample to keep ATTENTION compact; the agent reads the
        # full patch separately when they want the exact context.
        snippet = sample if len(sample) <= 140 else sample[:137].rstrip() + "…"
        out.append({"path": path, "sample": snippet})
    return out


def _write_executor_attention(
    *,
    project_root: Path,
    task_dir: Path,
    world_drift: list[world_baseline.DriftEntry],
    baseline_ref: world_baseline.BaselineRef | None,
    stale_units: list[tuple[UnitSelection, store.VersionRef]],
    fp: FingerprintIndex,
) -> dict[str, Any]:
    """Materialise `attention/` diffs + `business_processes/CLAUDE.md`.

    Called whenever the resolver picked at least one stale unit OR
    observed world drift. The Executor reads `business_processes/CLAUDE.md`
    automatically (Claude Code auto-loads CLAUDE.md from any directory it
    works in) so the ATTENTION header lands without us touching the
    Executor's root prompt.

    Returns a small summary that we attach to `instruction-selection.json`
    so post-run tooling can correlate "the Executor saw these diffs" with
    its eventual answer.
    """
    # SHA256 relocation report (vault/ + bin-help/) — an INDEPENDENT trigger.
    # A new / removed / moved file can warrant a global heads-up even when no
    # tracked world file drifted (e.g. an unindexed new `/docs/*` policy that
    # `/docs/README.md` does not yet reference, so world_drift is empty).
    # Computed up front so it can both gate the header and populate it.
    reloc_report: world_baseline.RelocationReport | None = None
    if baseline_ref is not None:
        reloc_report = world_baseline.merge_relocation_reports(
            [
                world_baseline.detect_relocations(
                    baseline_ref.version_dir / "vault",
                    task_dir / "vault",
                    rel_prefix="vault/",
                ),
                world_baseline.detect_relocations(
                    baseline_ref.snapshot_dir / "bin-help",
                    task_dir / "bin-help",
                    rel_prefix="bin-help/",
                ),
            ]
        )
        # Drop `added` files that nothing references — a dated scoped-update
        # distractor (`/docs/policy-updates/<dated>.md`, discovered by rule not
        # by link) is never in the selective baseline, so it would otherwise be
        # force-surfaced to the executor as a "new file" every trial.
        reloc_report = world_baseline.prune_unreferenced_added(
            reloc_report,
            current_trees=[
                (task_dir / "vault", "vault/"),
                (task_dir / "bin-help", "bin-help/"),
            ],
        )
    reloc_has = reloc_report is not None and reloc_report.has_content

    if not world_drift and not stale_units and not reloc_has:
        return {"world_diffs": [], "unit_diffs": []}

    attention_root = task_dir / ATTENTION_DIR_NAME
    written_world: list[dict[str, Any]] = []
    written_units: list[dict[str, Any]] = []
    # Per-diff dedup of "new references introduced by drift". Keyed by
    # path so the same ref mentioned in two world-files (e.g.
    # `/docs/returns.md` referenced from both /AGENTS.MD and
    # /docs/README.md) shows up once in the ATTENTION header.
    new_refs_by_path: dict[str, dict[str, Any]] = {}

    # 1. world-diffs/<slug>.patch
    if world_drift and baseline_ref is not None:
        wd_root = attention_root / "world-diffs"
        wd_root.mkdir(parents=True, exist_ok=True)
        for d in world_drift:
            rel = world_baseline.snapshot_rel(d.kind, d.path)
            old_path = baseline_ref.snapshot_dir / rel
            old_bytes = old_path.read_bytes() if old_path.is_file() else b""
            entry = fp.get(d.kind, d.path)
            current_bytes = entry.content or b""
            patch_text = _diff_lines(
                old_bytes=old_bytes,
                new_bytes=current_bytes,
                fromfile=f"baseline/{rel}",
                tofile=f"current/{rel}",
            )
            slug = rel.replace("/", "_")
            (wd_root / f"{slug}.patch").write_text(patch_text, encoding="utf-8")
            written_world.append(
                {
                    "kind": d.kind,
                    "path": d.path,
                    "status": d.status,
                    "patch": f"{ATTENTION_DIR_NAME}/world-diffs/{slug}.patch",
                }
            )
            for ref in _extract_new_refs(patch_text):
                # Earliest sighting wins on the sample, but record the
                # source files so the agent can find the full context.
                existing_ref = new_refs_by_path.get(ref["path"])
                if existing_ref is None:
                    new_refs_by_path[ref["path"]] = {
                        "path": ref["path"],
                        "sample": ref["sample"],
                        "sources": [d.path],
                    }
                elif d.path not in existing_ref["sources"]:
                    existing_ref["sources"].append(d.path)

    # 2. unit-diffs/<unit_id>/<slug>.patch
    if stale_units:
        ud_root = attention_root / "unit-diffs"
        ud_root.mkdir(parents=True, exist_ok=True)
        for sel, ref in stale_units:
            unit_dir = ud_root / sel.unit_id
            unit_dir.mkdir(parents=True, exist_ok=True)
            for m in sel.mismatches:
                rel = _snapshot_rel(m["kind"], m["path"])
                old_path = ref.snapshot_dir / rel
                old_bytes = old_path.read_bytes() if old_path.is_file() else b""
                entry = fp.get(m["kind"], m["path"])
                current_bytes = entry.content or b""
                patch_text = _diff_lines(
                    old_bytes=old_bytes,
                    new_bytes=current_bytes,
                    fromfile=f"{sel.unit_id}/{ref.version}/dependency_snapshot/{rel}",
                    tofile=f"current/{rel}",
                )
                slug = rel.replace("/", "_")
                (unit_dir / f"{slug}.patch").write_text(patch_text, encoding="utf-8")
                written_units.append(
                    {
                        "unit_id": sel.unit_id,
                        "kind": m["kind"],
                        "path": m["path"],
                        "patch": (
                            f"{ATTENTION_DIR_NAME}/unit-diffs/"
                            f"{sel.unit_id}/{slug}.patch"
                        ),
                    }
                )

    new_refs = sorted(new_refs_by_path.values(), key=lambda r: r["path"])

    # 3. attention/relocations.{md,json} — the full SHA256 rename/add/remove
    # map, written into the trial dir (not just the PA workdir) so the
    # executor gets the same general "what files moved/appeared/vanished"
    # view the world_refresh PA does. The ATTENTION header links to it.
    if reloc_report is not None and reloc_report.has_content:
        attention_root.mkdir(parents=True, exist_ok=True)
        (attention_root / "relocations.md").write_text(
            world_baseline.render_relocations_md(
                reloc_report, project_root=project_root
            ),
            encoding="utf-8",
        )
        (attention_root / "relocations.json").write_text(
            json.dumps(world_baseline.relocations_payload(reloc_report), indent=2)
            + "\n",
            encoding="utf-8",
        )

    # 4. business_processes/CLAUDE.md — written when a world file drifted OR
    # the relocation report found something. Both are foundation-wide signals
    # (new/changed policy, tool, SQL table, or a new/removed/moved file) that
    # warrant a global heads-up before the executor reads any BP. BP-only
    # drift is communicated via the per-file `Heads-up` block `_render_unit`
    # prepends — scoping that concern to the affected BP avoids telling the
    # executor that every other (matched) BP might also be wrong.
    if world_drift or reloc_has:
        bp_dir = task_dir / "business_processes"
        bp_dir.mkdir(parents=True, exist_ok=True)
        bp_claude = bp_dir / ATTENTION_BP_FILENAME
        existing = bp_claude.read_text(encoding="utf-8") if bp_claude.is_file() else ""
        attention_header = _render_bp_attention(
            world_drift=world_drift,
            baseline_ref=baseline_ref,
            stale_units=stale_units,
            new_refs=new_refs,
            reloc_report=reloc_report,
        )
        if existing:
            bp_claude.write_text(attention_header + "\n" + existing, encoding="utf-8")
        else:
            bp_claude.write_text(attention_header, encoding="utf-8")

    summary: dict[str, Any] = {
        "world_diffs": written_world,
        "unit_diffs": written_units,
        "new_refs": new_refs,
    }
    if reloc_report is not None and reloc_report.has_content:
        summary["relocations"] = world_baseline.relocations_payload(reloc_report)
    return summary


def _safe_write_executor_attention(
    *,
    label: str,
    project_root: Path,
    task_dir: Path,
    world_drift: list[world_baseline.DriftEntry],
    baseline_ref: world_baseline.BaselineRef | None,
    stale_units: list[tuple[UnitSelection, store.VersionRef]],
    fp: FingerprintIndex,
) -> dict[str, Any]:
    """`_write_executor_attention` with failure isolated to a warning.

    Attention/ diffs and the per-BP stale headers' diff links are
    *advisory*: the Executor can solve a trial without them as long as
    the rendered BP bodies and live workspace are intact. Aborting
    bootstrap because, say, a disk write to `attention/` failed would
    convert every advisory bug into a guaranteed task fail, even though
    the Executor never needed the file. Trap any exception, log it,
    and return an empty summary so the trial proceeds.
    """
    try:
        return _write_executor_attention(
            project_root=project_root,
            task_dir=task_dir,
            world_drift=world_drift,
            baseline_ref=baseline_ref,
            stale_units=stale_units,
            fp=fp,
        )
    except Exception as exc:
        if label:
            print(
                f"{label} [resolver] WARN: attention/ rendering failed: "
                f"{exc!r}; executor will start without diff machinery"
            )
        else:
            print(
                f"warn: attention/ rendering failed: {exc!r}; "
                "executor will start without diff machinery"
            )
        return {
            "world_diffs": [],
            "unit_diffs": [],
            "new_refs": [],
            "error": repr(exc),
        }


def _reloc_display_path(p: str) -> str:
    """Render a relocation path for the executor: `vault/docs/x.md` → `/docs/x.md`.

    `vault/`-relative paths are workspace paths the executor reads at their
    absolute `/...` location; `bin-help/...` paths stay as-is.
    """
    return "/" + p[len("vault/"):] if p.startswith("vault/") else p


def _render_bp_attention(
    *,
    world_drift: list[world_baseline.DriftEntry],
    baseline_ref: world_baseline.BaselineRef | None,
    stale_units: list[tuple[UnitSelection, store.VersionRef]],
    new_refs: list[dict[str, Any]] | None = None,
    reloc_report: world_baseline.RelocationReport | None = None,
) -> str:
    """Format the ATTENTION header rendered into
    `business_processes/CLAUDE.md`."""
    del baseline_ref  # internal-only; agent doesn't need the version label
    lines: list[str] = [
        "# ATTENTION — some business-process files below may be out of date",
        "",
        (
            "Since these BP files were drafted, the live workspace has "
            "changed. The BPs may quote sentences that no longer exist, or "
            "omit ones that now do. When a BP description disagrees with "
            "what you read live via `execute_python`, **trust the live read** "
            "and adjust your plan."
        ),
        "",
    ]
    if reloc_report is not None and reloc_report.has_content:
        lines.extend(
            [
                "## Files that moved, appeared, or were removed",
                "",
                (
                    "The live workspace's file set changed since these BP files "
                    "were drafted. Full SHA256 map (proof for each move): "
                    f"[relocations.md](../{ATTENTION_DIR_NAME}/relocations.md). "
                    "Highlights:"
                ),
                "",
            ]
        )
        if reloc_report.relocations:
            lines.extend(
                [
                    "**Moved** (same content, new path) — a BP may name the "
                    "**old** path; read it live at the new path, don't waste a "
                    "tool call hunting for it:",
                    "",
                    "| BP references (old path) | read it live at (new path) |",
                    "|---|---|",
                ]
            )
            for r in reloc_report.relocations:
                lines.append(
                    f"| `{_reloc_display_path(r.old_path)}` "
                    f"| `{_reloc_display_path(r.new_path)}` |"
                )
            lines.append("")
        if reloc_report.renamed_changed:
            lines.extend(
                [
                    "**Renamed & changed** — almost certainly the same file at a "
                    "new path, but its content ALSO changed. A BP may name the "
                    "**old** path and quote its **old** wording; read the **new** "
                    "path live and trust what you read over the BP:",
                    "",
                    "| BP references (old path) | read it live at (new path) |",
                    "|---|---|",
                ]
            )
            for r in reloc_report.renamed_changed:
                lines.append(
                    f"| `{_reloc_display_path(r.old_path)}` "
                    f"| `{_reloc_display_path(r.new_path)}` |"
                )
            lines.append("")
        if reloc_report.added:
            lines.extend(
                [
                    "**New files** — not covered by any BP in this directory. "
                    "If one is relevant to your task, open it via "
                    "`execute_python` and treat what you read as the source of "
                    "truth:",
                    "",
                ]
            )
            lines.extend(f"- `{_reloc_display_path(p)}`" for p in reloc_report.added)
            lines.append("")
        if reloc_report.removed:
            lines.extend(
                [
                    "**Removed** — gone from the live world; a BP that relies "
                    "on one of these is obsolete for that part:",
                    "",
                ]
            )
            lines.extend(f"- `{_reloc_display_path(p)}`" for p in reloc_report.removed)
            lines.append("")
    if world_drift:
        lines.extend(
            [
                "## Live workspace files that have changed",
                "",
                (
                    "These files are general-purpose references — they are "
                    "quoted from, or linked to, by most BP files in this "
                    "directory. Skim each diff before applying a BP that "
                    "touches the same area; the additions tend to introduce "
                    "**new policies, new tool subcommands, or new SQL "
                    "tables** the BPs cannot know about."
                ),
                "",
            ]
        )
        for d in world_drift:
            rel = world_baseline.snapshot_rel(d.kind, d.path)
            slug = rel.replace("/", "_")
            label = d.path if d.kind == "workspace" else f"bin-help/{d.path}"
            lines.append(
                f"- `{label}` — "
                f"[diff](../{ATTENTION_DIR_NAME}/world-diffs/{slug}.patch)"
            )
        lines.append("")
    if stale_units:
        lines.extend(
            [
                "## BP files flagged as out of date",
                "",
                (
                    "These BPs were drafted against earlier copies of the "
                    "files listed beside each one. Each BP file starts with "
                    "a `Heads-up — this process may be out of date` block "
                    "repeating this warning. The diff shows the old text "
                    "the BP saw versus what you'll see when you read the "
                    "file live."
                ),
                "",
            ]
        )
        for sel, _ref in stale_units:
            bp_name = Path(sel.render_to).name
            deps_str = ", ".join(f"`{m['path']}`" for m in sel.mismatches)
            lines.append(f"- [`{bp_name}`]({bp_name}) — changed: {deps_str}")
            for m in sel.mismatches:
                rel = _snapshot_rel(m["kind"], m["path"])
                slug = rel.replace("/", "_")
                lines.append(
                    f"  - [diff](../{ATTENTION_DIR_NAME}/unit-diffs/"
                    f"{sel.unit_id}/{slug}.patch)"
                )
        lines.append("")
    if new_refs:
        lines.extend(
            [
                "## New files / tools the diffs introduce",
                "",
                (
                    "Each entry below is a path or tool invocation that "
                    "appears only in the **added** lines of the diffs — it "
                    "is not in any BP file in this directory. If the named "
                    "subject is relevant to your task, open the path via "
                    "`execute_python` and treat what you read as the source "
                    "of truth. Skip entries unrelated to the current trial."
                ),
                "",
            ]
        )
        for ref in new_refs:
            sources = ", ".join(f"`{s}`" for s in ref.get("sources", []))
            sample = ref.get("sample", "").strip()
            line = f"- `{ref['path']}`"
            if sources:
                line += f" — introduced by edits to {sources}"
            lines.append(line)
            if sample:
                lines.append(f"  > {sample}")
        lines.append("")
    lines.extend(
        [
            "## How to use this header",
            "",
            (
                "1. Open each `*.patch` link above before reading any BP "
                "file that touches the same area."
            ),
            (
                "2. A new `/docs/...` policy, a new `/bin/<tool>` "
                "subcommand, or a new SQL column shown in a diff is "
                "**not** covered by any BP — discover it from the live "
                "workspace via `execute_python`."
            ),
            (
                "3. When a diff removes a sentence quoted by a BP, treat "
                "the BP sentence as obsolete."
            ),
            (
                "4. The live workspace is always the source of truth — "
                "`Read` `/AGENTS.MD`, `/docs/*`, and `/bin/<tool> --help` "
                "directly whenever a BP and live state disagree."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _write_selection(
    *,
    task_dir: Path,
    task_id: str,
    trial_id: str,
    result: SelectionResult,
) -> None:
    units_payload: list[dict[str, Any]] = []
    for u in result.units:
        entry: dict[str, Any] = {
            "unit_id": u.unit_id,
            "kind": u.kind,
            "render_to": u.render_to,
            "selected_version": u.selected_version,
            "selection_status": u.selection_status,
            "matched_dependencies": u.matched_dependencies,
        }
        if u.mismatches:
            entry["mismatches"] = u.mismatches
        units_payload.append(entry)
    payload: dict[str, Any] = {
        "status": result.status,
        "stale_resolution": result.stale_resolution,
        "task_id": task_id,
        "trial_id": trial_id,
        "executor_started": result.executor_started,
        "units": units_payload,
    }
    if result.pa_refresh is not None:
        payload["pa_refresh"] = result.pa_refresh
    if result.world_refresh is not None:
        payload["world_refresh"] = result.world_refresh
    if result.world_drift is not None:
        payload["world_drift"] = result.world_drift
    if result.attention is not None:
        payload["attention"] = result.attention
    if result.fatal_errors:
        payload["fatal_errors"] = result.fatal_errors
    (_logs_dir(task_dir) / "instruction-selection.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def _write_stale_report(
    *,
    task_dir: Path,
    stale_units: list[tuple[UnitSelection, store.VersionRef, store.Manifest]],
) -> None:
    units_payload: list[dict[str, Any]] = []
    for sel, ref, manifest in stale_units:
        units_payload.append(
            {
                "unit_id": sel.unit_id,
                "selected_version": ref.version,
                "render_to": sel.render_to,
                "mismatches": sel.mismatches,
                "manifest_dependency_count": len(manifest.dependencies),
            }
        )
    payload = {
        "stale_units": units_payload,
    }
    (_logs_dir(task_dir) / "instruction-stale-report.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


async def resolve_and_render(
    *,
    project_root: Path,
    task_dir: Path,
    task_id: str,
    trial_id: str,
    stale_resolution: str,
    pa_queue: Any | None,
    substitutions: dict[str, str],
    label: str = "",
) -> SelectionResult:
    """Top-level bootstrap entry point.

    Always renders something into the task dir, so the Executor can start
    even when the PA refresh path fails. Raises only when the registry
    points at a unit with no installable versions — that is an operator
    problem (e.g. retired-only) that needs human attention before any
    trial can run.
    """
    if stale_resolution not in VALID_STALE_RESOLUTIONS:
        raise ValueError(
            f"unknown STALE_RESOLUTION={stale_resolution!r}; "
            f"choose one of {VALID_STALE_RESOLUTIONS}"
        )

    # Resolve trial-static placeholders in the always-present BP attention
    # file (bootstrap copies it verbatim, so it bypasses `_render_unit`).
    # Up front, before the world-drift header may be prepended below.
    _render_static_bp_attention(task_dir, substitutions)

    registry = store.load_registry(project_root)
    fp = FingerprintIndex(task_dir=task_dir, project_root=project_root)
    baseline_ref = world_baseline.get_latest_baseline(project_root)
    baseline_manifest = (
        world_baseline.load_baseline_manifest(baseline_ref)
        if baseline_ref is not None
        else None
    )
    # Effective world-file set = explicit world.json + the auto-discovered
    # /bin tool surface (variant B). Both the drift check and the
    # matcher-skip signature set are derived from it so every contour
    # (executor ATTENTION, world_refresh, per-unit matcher) agrees on the
    # same world-file set.
    world_files = world_baseline.effective_world_files(
        project_root, fp, baseline_manifest
    )
    world_sigs = world_baseline.world_dep_signatures(world_files)

    # ── World drift check (before per-unit selection) ──
    world_refresh_info: dict[str, Any] | None = None
    world_drift_payload: list[dict[str, Any]] | None = None
    # `drift_entries` is the typed list we keep around for `attention/`
    # diff writing. It is recomputed in the wait_for_refresh path so the
    # diff we hand to the Executor reflects the new baseline (or stays
    # populated when the PA refresh failed).
    drift_entries: list[world_baseline.DriftEntry] = []
    if baseline_ref is None:
        # Empty baseline: skip the drift check. If --world-create is on,
        # fire a one-off seed `world_create` job — the resolver-level
        # dedup (`_world_refresh_dedup["seed"]`) makes sure only the
        # first trial actually queues it.
        if (
            pa_queue is not None
            and not pa_queue.disabled
            and pa_queue.world_create_enabled
        ):
            from . import pa_workdir
            if stale_resolution == STALE_RESOLUTION_WAIT:
                world_refresh_info = await pa_workdir.run_world_create_blocking(
                    task_dir=task_dir,
                    task_id=task_id,
                    trial_id=trial_id,
                    baseline_ref=None,
                    drift=[],
                    pa_queue=pa_queue,
                    label=label,
                )
            else:
                world_refresh_info = await pa_workdir.enqueue_async_world_create(
                    task_dir=task_dir,
                    task_id=task_id,
                    trial_id=trial_id,
                    baseline_ref=None,
                    drift=[],
                    pa_queue=pa_queue,
                    label=label,
                )
        elif label:
            print(
                f"{label} [resolver] world_baseline empty — skipping drift check. "
                "Run `bp_admin world-baseline init --from-task-dir <path>` or "
                "pass `--world-create` to seed v0001 via PA."
            )
    else:
        drift_entries = world_baseline.compute_drift(baseline_manifest, fp, world_files)
        if drift_entries:
            world_drift_payload = [
                {
                    "kind": d.kind,
                    "path": d.path,
                    "status": d.status,
                    "baseline_sha256": d.baseline_sha256,
                    "current_sha256": d.current_sha256,
                    "why": d.why,
                }
                for d in drift_entries
            ]
            if label:
                files_str = ", ".join(f"`{d.path}`" for d in drift_entries)
                print(
                    f"{label} [resolver] world drift vs {baseline_ref.version}: "
                    f"{len(drift_entries)} file(s): {files_str}"
                )
            if (
                pa_queue is not None
                and not pa_queue.disabled
                and (
                    pa_queue.world_refresh_enabled
                    or pa_queue.world_create_enabled
                )
            ):
                from . import pa_workdir
                use_create = pa_queue.world_create_enabled
                if stale_resolution == STALE_RESOLUTION_WAIT:
                    blocking = (
                        pa_workdir.run_world_create_blocking
                        if use_create
                        else pa_workdir.run_world_refresh_blocking
                    )
                    world_refresh_info = await blocking(
                        task_dir=task_dir,
                        task_id=task_id,
                        trial_id=trial_id,
                        baseline_ref=baseline_ref,
                        drift=drift_entries,
                        pa_queue=pa_queue,
                        label=label,
                    )
                    # After blocking world-PA, registry may have new
                    # units and baseline advanced — re-load both. Fresh
                    # FingerprintIndex too (snapshots changed under us).
                    registry = store.load_registry(project_root)
                    fp = FingerprintIndex(
                        task_dir=task_dir, project_root=project_root
                    )
                    # Re-check drift against the (possibly-advanced) baseline
                    # so any remaining drift still surfaces in attention/.
                    baseline_ref = world_baseline.get_latest_baseline(project_root)
                    if baseline_ref is not None:
                        baseline_manifest = world_baseline.load_baseline_manifest(
                            baseline_ref
                        )
                        # Re-derive the effective world-file set + matcher
                        # signatures against the advanced baseline (it now
                        # snapshots the auto-tracked /bin helps).
                        world_files = world_baseline.effective_world_files(
                            project_root, fp, baseline_manifest
                        )
                        world_sigs = world_baseline.world_dep_signatures(world_files)
                        drift_entries = world_baseline.compute_drift(
                            baseline_manifest, fp, world_files
                        )
                    else:
                        drift_entries = []
                else:
                    enqueue = (
                        pa_workdir.enqueue_async_world_create
                        if use_create
                        else pa_workdir.enqueue_async_world_refresh
                    )
                    world_refresh_info = await enqueue(
                        task_dir=task_dir,
                        task_id=task_id,
                        trial_id=trial_id,
                        baseline_ref=baseline_ref,
                        drift=drift_entries,
                        pa_queue=pa_queue,
                        label=label,
                    )

    selections: list[UnitSelection] = []
    stale_units: list[tuple[UnitSelection, store.VersionRef, store.Manifest]] = []
    fatal: list[str] = []

    for reg in registry:
        ref, status, manifest, mismatches = _select_one(project_root, reg.id, fp, world_sigs)
        sel = UnitSelection(
            unit_id=reg.id,
            kind=reg.kind,
            render_to=reg.render_to,
            selected_version=ref.version if ref else None,
            selection_status=status,
            mismatches=mismatches,
            matched_dependencies=(
                len(manifest.dependencies) if manifest and status == MATCHED else 0
            ),
        )
        selections.append(sel)
        if status in (NO_VERSIONS, RETIRED_ONLY):
            fatal.append(f"unit {reg.id!r}: {status}")
            continue
        if status == STALE_LATEST_FALLBACK and ref is not None and manifest is not None:
            stale_units.append((sel, ref, manifest))

    if fatal:
        result = SelectionResult(
            status="bootstrap_failed",
            stale_resolution=stale_resolution,
            units=selections,
            executor_started=False,
            pa_refresh=None,
            world_refresh=world_refresh_info,
            world_drift=world_drift_payload,
            fatal_errors=fatal,
        )
        _write_selection(
            task_dir=task_dir, task_id=task_id, trial_id=trial_id, result=result
        )
        raise RuntimeError(
            "instruction resolver — bootstrap-fatal: " + "; ".join(fatal)
        )

    # All units have a selection. Decide stale path.
    if not stale_units:
        # All matched.
        for sel in selections:
            assert sel.selected_version is not None
            ref = store.get_version(project_root, sel.unit_id, sel.selected_version)
            assert ref is not None
            _render_unit(sel=sel, ref=ref, task_dir=task_dir, is_stale=False, substitutions=substitutions)
        # Even when every per-unit dep matched, the world layer may
        # still be drifting (per-unit matcher skips world-deps). Surface
        # the drift to the Executor here so it doesn't apply policy from
        # a stale baseline.
        attention_summary = _safe_write_executor_attention(
            label=label,
            project_root=project_root,
            task_dir=task_dir,
            world_drift=drift_entries,
            baseline_ref=baseline_ref,
            stale_units=[],
            fp=fp,
        )
        result = SelectionResult(
            status=MATCHED,
            stale_resolution=stale_resolution,
            units=selections,
            executor_started=True,
            pa_refresh=None,
            world_refresh=world_refresh_info,
            world_drift=world_drift_payload,
            attention=attention_summary,
        )
        _write_selection(
            task_dir=task_dir, task_id=task_id, trial_id=trial_id, result=result
        )
        if label:
            print(f"{label} [resolver] matched {len(selections)} units")
        return result

    _write_stale_report(task_dir=task_dir, stale_units=stale_units)

    pa_refresh_info: dict[str, Any] | None = None

    if (
        stale_resolution == STALE_RESOLUTION_WAIT
        and pa_queue is not None
        and not pa_queue.disabled
        and pa_queue.refresh_enabled
    ):
        from .pa_workdir import run_refresh_blocking

        pa_refresh_info = await run_refresh_blocking(
            task_dir=task_dir,
            task_id=task_id,
            trial_id=trial_id,
            stale_units=[(sel.unit_id, ref.version) for sel, ref, _ in stale_units],
            pa_queue=pa_queue,
            label=label,
        )
        completions_by_unit: dict[str, str] = {}
        if pa_refresh_info:
            for c in pa_refresh_info.get("completions") or []:
                completions_by_unit[c["unit_id"]] = c.get(
                    "terminal_status", "failed"
                )
        # Re-resolve with a fresh fingerprint index (snapshots changed).
        fp2 = FingerprintIndex(task_dir=task_dir, project_root=project_root)
        rerun: list[UnitSelection] = []
        for reg in registry:
            ref, status, manifest, mismatches = _select_one(project_root, reg.id, fp2, world_sigs)
            sel = UnitSelection(
                unit_id=reg.id,
                kind=reg.kind,
                render_to=reg.render_to,
                selected_version=ref.version if ref else None,
                selection_status=status,
                mismatches=mismatches,
                matched_dependencies=(
                    len(manifest.dependencies)
                    if manifest and status == MATCHED
                    else 0
                ),
            )
            if status == STALE_LATEST_FALLBACK:
                pa_term = completions_by_unit.get(reg.id)
                if pa_term in (None, "failed", "rejected", "timeout"):
                    sel.selection_status = STALE_REFRESH_FAILED
                else:
                    sel.selection_status = STALE_REFRESH_INCOMPLETE
            rerun.append(sel)
        rerun_stale: list[tuple[UnitSelection, store.VersionRef]] = []
        for sel in rerun:
            if sel.selected_version is None:
                continue
            ref = store.get_version(project_root, sel.unit_id, sel.selected_version)
            assert ref is not None
            is_stale = sel.selection_status != MATCHED
            _render_unit(sel=sel, ref=ref, task_dir=task_dir, is_stale=is_stale, substitutions=substitutions)
            if is_stale:
                rerun_stale.append((sel, ref))
        # After wait_for_refresh, drift_entries reflects whatever the PA
        # advance left behind (empty when PA succeeded, populated when it
        # failed). Either way the Executor sees an accurate ATTENTION.
        attention_summary = _safe_write_executor_attention(
            label=label,
            project_root=project_root,
            task_dir=task_dir,
            world_drift=drift_entries,
            baseline_ref=baseline_ref,
            stale_units=rerun_stale,
            fp=fp,
        )
        all_matched = all(s.selection_status == MATCHED for s in rerun)
        result = SelectionResult(
            status=MATCHED_AFTER_REFRESH if all_matched else STALE_REFRESH_INCOMPLETE,
            stale_resolution=stale_resolution,
            units=rerun,
            executor_started=True,
            pa_refresh=pa_refresh_info,
            world_refresh=world_refresh_info,
            world_drift=world_drift_payload,
            attention=attention_summary,
        )
        _write_selection(
            task_dir=task_dir, task_id=task_id, trial_id=trial_id, result=result
        )
        if label:
            print(
                f"{label} [resolver] wait_for_refresh: {result.status} "
                f"({sum(1 for s in rerun if s.selection_status == MATCHED)} matched)"
            )
        return result

    # latest_async_refresh OR no queue → render stale fallback now,
    # optionally queue PA refresh in background. (When world_refresh
    # already kicked off this run, `submit_refresh` resolves immediately
    # to `skipped` — the queue prevents per-unit PA work whose answer
    # would be stale once the world advances. When REFRESH_ENABLED=0 the
    # per-unit refresh mode is gated off entirely: render stale fallback,
    # enqueue nothing.)
    if (
        pa_queue is not None
        and not pa_queue.disabled
        and pa_queue.refresh_enabled
    ):
        from .pa_workdir import enqueue_async_refreshes

        pa_refresh_info = await enqueue_async_refreshes(
            task_dir=task_dir,
            task_id=task_id,
            trial_id=trial_id,
            stale_units=[(sel.unit_id, ref.version) for sel, ref, _ in stale_units],
            pa_queue=pa_queue,
            label=label,
        )
    for sel in selections:
        if sel.selected_version is None:
            continue
        ref = store.get_version(project_root, sel.unit_id, sel.selected_version)
        assert ref is not None
        is_stale = sel.selection_status != MATCHED
        _render_unit(sel=sel, ref=ref, task_dir=task_dir, is_stale=is_stale, substitutions=substitutions)
    attention_summary = _safe_write_executor_attention(
        label=label,
        project_root=project_root,
        task_dir=task_dir,
        world_drift=drift_entries,
        baseline_ref=baseline_ref,
        stale_units=[(sel, ref) for sel, ref, _ in stale_units],
        fp=fp,
    )
    result = SelectionResult(
        status=STALE_LATEST_FALLBACK,
        stale_resolution=stale_resolution,
        units=selections,
        executor_started=True,
        pa_refresh=pa_refresh_info,
        world_refresh=world_refresh_info,
        world_drift=world_drift_payload,
        attention=attention_summary,
    )
    _write_selection(
        task_dir=task_dir, task_id=task_id, trial_id=trial_id, result=result
    )
    if label:
        print(
            f"{label} [resolver] stale_latest_fallback: "
            f"{len(stale_units)} stale, "
            f"{sum(1 for s in selections if s.selection_status == MATCHED)} matched"
        )
    return result
