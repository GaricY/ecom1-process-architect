"""Build PA workdirs for every mode (failure_fix, fix_blind, refresh,
world_refresh, world_create) and ingest decision output. Workdirs all
live next to the originating task dir (refresh / world_* next to the
bootstrap-time `task_dir`, fix / fix_blind next to the failed
`task_dir`).

Schema-v2 layouts (task-022 §6.2-§6.5) — only what PA SEES at spawn
is enumerated; post-run artefacts (`pa-result.json`, `report_PA.md`,
`.logs/dump`, `conflict-history.json`, …) appear later and are not
part of the contract.

failure_fix / fix_blind workdir (§6.5):

```
<failed_task_dir>-process-architect[-blind]/
  CLAUDE.md                    # failure_fix.md or fix_blind.md
  failure-fix-task.md          # brief (no score for fix_blind)
  task.md scratchpad.json state.json answer.json
  vault/ bin-help/             # copied from failed task_dir
  selected-instructions/
    instruction-selection.json
    units/<unit_id>/{version.txt, content.md, manifest.json}
  version-history/             # registry.json + prompts/process_architect/
                               #   + units/<id>/v*/{content,manifest,changes,diff}
  .logs/executor_actions.md mcp-tool-calls.jsonl ...
  pa-output/                   # PA writes here
```

refresh workdir (§6.4):

```
<task_dir>-process-architect-refresh-<unit_id>/
  CLAUDE.md                    # refresh.md (self-contained)
  bin-help/ vault/             # mirror of trial dump
  unit-deps-diff.patch         # concat: unit deps + world deps,
                               #   baseline-snapshot vs current
  processes/active/<unit_id>/  # latest content.md + manifest.json
  processes/{author-contract.md, inventory.md, registry.json}
  version-history/             # full unit revision tree; NO drafts,
                               #   NO world_baseline (per task-022 §13.1)
  pa-output/                   # PA writes here
```

world_refresh / world_create workdir (§6.2 + §6.3):

```
<task_dir>-process-architect-world-{refresh|create}-<baseline_or_seed>/
  CLAUDE.md                    # world_refresh.md or world_create.md
  bin-help/ vault/             # mirror of trial dump
  bin-help-diff.patch          # FULL tool/command + SQL schema diff (key signal)
  world-changes.md             # vault triage index (edits/moved/new/removed), read first
  world-edits.patch            # LEAN patch: only surgical vault content deltas
  relocations.json             # machine-readable file-set map (rename/new/removed)
  processes/active/<bp_id>/    # all active units (read-only context)
  processes/drafts/<bp_id>.md  # from agent/instructions/units_draft/
  processes/{author-contract.md, inventory.md, registry.json}
  pa-output/                   # PA writes here
```

Output ingestion: `pa-output/pa-decision.json` is validated against
the expected mode; if it clears every check the writer creates a new
version per `changes[]` / `changes_refresh[]` entry (and a new
baseline for world_* modes when `advance_baseline` is true). On
validation failure, `pa-output/rejected.json` is written and no
version lands. With `PA_APPLY=0` the apply step is replaced by a
`dry-run-summary.md` next to `pa-output/`.
"""

from __future__ import annotations

import asyncio
import difflib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..bootstrap import world_samples_dir
from . import pa_decision, pa_runner, store, versioning, world_baseline
from .fingerprints import FingerprintIndex
from .pa_queue import (
    PRIORITY_ASYNC,
    PRIORITY_BLOCKING,
    PRIORITY_LABELS,
    PRIORITY_WORLD_REFRESH,
    PaJob,
    PaJobResult,
    PaQueue,
)


@dataclass
class PaWorkerConfig:
    project_root: Path
    claude_bin: str
    model: str
    effort: str
    max_turns: int
    timeout_sec: float
    world_timeout_sec: float
    conflict_mode: bool = True
    conflict_max_retries: int = 1
    pa_apply: bool = True


def make_pa_worker(config: PaWorkerConfig):
    async def worker(queue: PaQueue, job: PaJob) -> PaJobResult:
        if job.kind == "refresh":
            return await _execute_refresh(queue=queue, job=job, config=config)
        if job.kind == "failure_fix":
            return await _execute_failure_fix(queue=queue, job=job, config=config, mode="failure_fix")
        if job.kind == "fix_blind":
            return await _execute_failure_fix(queue=queue, job=job, config=config, mode="fix_blind")
        if job.kind == "world_refresh":
            return await _execute_world_refresh(queue=queue, job=job, config=config)
        if job.kind == "world_create":
            return await _execute_world_create(queue=queue, job=job, config=config)
        return PaJobResult(
            job_id=job.job_id,
            kind=job.kind,
            priority=PRIORITY_LABELS[job.priority],
            terminal_status="failed",
            duration_ms=0,
            error=f"unknown job kind {job.kind!r}",
        )

    return worker


# ── Refresh ──────────────────────────────────────────────────────────────


async def enqueue_async_refreshes(
    *,
    task_dir: Path,
    task_id: str,
    trial_id: str,
    stale_units: list[tuple[str, str]],
    pa_queue: PaQueue,
    label: str = "",
) -> dict[str, Any]:
    """Stale units → one refresh PA job per unit, priority=async, no wait.

    Workdir is NOT built here — only the path and payload land in the
    queue. `_execute_refresh` materialises the workdir when the slot
    opens, so the snapshot of `version-history/` reflects whatever has
    been published by then (incl. concurrent failure_fix outputs).
    """
    jobs: list[dict[str, Any]] = []
    for unit_id, base_version in stale_units:
        pa_dir = task_dir.parent / f"{task_dir.name}-process-architect-refresh-{unit_id}"
        payload = {
            "pa_dir": str(pa_dir),
            "task_dir": str(task_dir),
            "task_id": task_id,
            "trial_id": trial_id,
            "unit_id": unit_id,
            "base_version": base_version,
        }
        _, is_new = pa_queue.submit_refresh(
            unit_id=unit_id, payload=payload, priority=PRIORITY_ASYNC
        )
        jobs.append(
            {
                "unit_id": unit_id,
                "queue_priority": PRIORITY_LABELS[PRIORITY_ASYNC],
                "waited": False,
                "is_new_job": is_new,
            }
        )
        if label:
            kind_suffix = "new" if is_new else "joined existing"
            print(f"{label} [resolver] queued refresh for {unit_id} ({kind_suffix})")
    return {"jobs": jobs}


async def run_refresh_blocking(
    *,
    task_dir: Path,
    task_id: str,
    trial_id: str,
    stale_units: list[tuple[str, str]],
    pa_queue: PaQueue,
    label: str = "",
) -> dict[str, Any]:
    """Stale units → blocking refresh per unit, wait for all.

    Same deferred-materialise rule as `enqueue_async_refreshes`.
    """
    awaits: list[tuple[str, asyncio.Future[PaJobResult]]] = []
    job_summaries: list[dict[str, Any]] = []
    for unit_id, base_version in stale_units:
        pa_dir = task_dir.parent / f"{task_dir.name}-process-architect-refresh-{unit_id}"
        payload = {
            "pa_dir": str(pa_dir),
            "task_dir": str(task_dir),
            "task_id": task_id,
            "trial_id": trial_id,
            "unit_id": unit_id,
            "base_version": base_version,
        }
        future, is_new = pa_queue.submit_refresh(
            unit_id=unit_id, payload=payload, priority=PRIORITY_BLOCKING
        )
        awaits.append((unit_id, future))
        job_summaries.append(
            {
                "unit_id": unit_id,
                "queue_priority": PRIORITY_LABELS[PRIORITY_BLOCKING],
                "waited": True,
                "is_new_job": is_new,
            }
        )
    results = await asyncio.gather(*(f for _, f in awaits), return_exceptions=True)
    completions: list[dict[str, Any]] = []
    for (unit_id, _), res in zip(awaits, results):
        if isinstance(res, BaseException):
            completions.append(
                {"unit_id": unit_id, "terminal_status": "failed", "error": repr(res)}
            )
        else:
            completions.append(
                {
                    "unit_id": unit_id,
                    "terminal_status": res.terminal_status,
                    "created_versions": res.created_versions,
                    "error": res.error,
                }
            )
    if label:
        print(
            f"{label} [resolver] wait_for_refresh: "
            f"{sum(1 for c in completions if c['terminal_status'] == 'completed')}/"
            f"{len(completions)} refreshes completed"
        )
    return {"jobs": job_summaries, "completions": completions}


def _materialise_refresh_workdir(
    *,
    project_root: Path,
    pa_dir: Path,
    task_id: str,
    trial_id: str,
    unit_id: str,
    ref: store.VersionRef,
    manifest: store.Manifest,
    fp: FingerprintIndex,
    task_dir: Path,
) -> None:
    """Schema-v2 layout (task-022 §6.4):

        <pa_dir>/
          CLAUDE.md                       # = refresh.md (self-contained)
          bin-help/                       # mirror task_dir/bin-help/
          unit-deps-diff.patch            # concat: snapshot vs current,
                                          #   unit deps + world deps
          pa-output/
          processes/
            active/<unit_id>/{content.md, manifest.json}
            author-contract.md
            inventory.md
            registry.json
          vault/                          # mirror task_dir/vault/
          version-history/
            registry.json
            units/<id>/<vNNNN>/...
            prompts/process_architect/
          .claude/settings.json
    """
    if pa_dir.exists():
        shutil.rmtree(pa_dir)
    pa_dir.mkdir(parents=True)

    prompts = store.pa_prompts_dir(project_root)
    (pa_dir / "CLAUDE.md").write_text(
        pa_runner.assemble_claude_md(prompts, mode="refresh"), encoding="utf-8"
    )
    pa_runner.write_pa_settings(pa_dir)

    # vault/ + bin-help/ — full mirrors of the trial dump.
    vault_src = task_dir / "vault"
    if vault_src.is_dir():
        shutil.copytree(vault_src, pa_dir / "vault", dirs_exist_ok=True)
    bin_help_src = task_dir / "bin-help"
    if bin_help_src.is_dir():
        shutil.copytree(bin_help_src, pa_dir / "bin-help", dirs_exist_ok=True)

    # processes/ — author-contract, inventory, registry, active snapshot
    # of the single stale unit. Drafts deliberately NOT copied (per
    # task-022 §refresh).
    proc_dir = pa_dir / "processes"
    (proc_dir / "active").mkdir(parents=True, exist_ok=True)

    contract_src = prompts / "bp_author_contract.md"
    if contract_src.is_file():
        shutil.copyfile(contract_src, proc_dir / "author-contract.md")
    registry_src = store.registry_path(project_root)
    if registry_src.is_file():
        shutil.copyfile(registry_src, proc_dir / "registry.json")
    (proc_dir / "inventory.md").write_text(
        _render_bps_inventory(project_root), encoding="utf-8"
    )
    unit_target = proc_dir / "active" / unit_id
    unit_target.mkdir(parents=True, exist_ok=True)
    if ref.content_path.is_file():
        shutil.copyfile(ref.content_path, unit_target / "content.md")
    if ref.manifest_path.is_file():
        shutil.copyfile(ref.manifest_path, unit_target / "manifest.json")

    # unit-deps-diff.patch — concat of unit deps + world deps.
    # Unit deps: old bytes from `ref.snapshot_dir / snap_rel`, current
    # bytes from `fp.get(...)`. World deps: old bytes from the latest
    # baseline snapshot, current bytes from `fp.get(...)`.
    chunks: list[str] = []
    for dep in manifest.dependencies:
        if not dep.required:
            continue
        snap_rel = _snapshot_rel(dep.kind, dep.path)
        old_path = ref.snapshot_dir / snap_rel
        old_bytes = old_path.read_bytes() if old_path.is_file() else b""
        entry = fp.get(dep.kind, dep.path)
        current_bytes = entry.content or b""
        old_text = _decode(old_bytes)
        cur_text = _decode(current_bytes)
        if old_text == cur_text:
            continue
        chunks.extend(
            difflib.unified_diff(
                old_text.splitlines(keepends=True),
                cur_text.splitlines(keepends=True),
                fromfile=f"unit_dep/{snap_rel}",
                tofile=f"current/{snap_rel}",
            )
        )

    baseline_ref = world_baseline.get_latest_baseline(project_root)
    world_files = world_baseline.load_world_files(project_root)
    for wf in world_files:
        wb_rel = world_baseline.snapshot_rel(wf.kind, wf.path)
        old_bytes = b""
        if baseline_ref is not None:
            src = baseline_ref.snapshot_dir / wb_rel
            if src.is_file():
                old_bytes = src.read_bytes()
        entry = fp.get(wf.kind, wf.path)
        current_bytes = entry.content or b""
        old_text = _decode(old_bytes)
        cur_text = _decode(current_bytes)
        if old_text == cur_text:
            continue
        chunks.extend(
            difflib.unified_diff(
                old_text.splitlines(keepends=True),
                cur_text.splitlines(keepends=True),
                fromfile=f"world_dep/{wb_rel}",
                tofile=f"current/{wb_rel}",
            )
        )

    (pa_dir / "unit-deps-diff.patch").write_text(
        "".join(chunks), encoding="utf-8"
    )

    # version-history/ — full revision tree of every registered unit.
    # world_baseline/ deliberately NOT copied (task-022 §13.1).
    all_unit_ids = [u.id for u in store.load_registry(project_root)]
    _materialise_version_history(
        project_root=project_root,
        pa_dir=pa_dir,
        unit_ids=all_unit_ids,
    )

    (pa_dir / "pa-output").mkdir(parents=True, exist_ok=True)

    # `task_id`, `trial_id` intentionally not surfaced as files — PA
    # reads CLAUDE.md + the diff, audit context goes into post-run
    # `report_PA.md` + `pa-result.json` (see §6.1).
    _ = task_id, trial_id


def _decode(b: bytes) -> str:
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("utf-8", errors="replace")


def _read_user_prompt(project_root: Path, mode: str) -> str:
    """Read the user-prompt that gets piped to claude CLI for `mode`."""
    path = store.pa_user_prompt_path(project_root, mode)
    if not path.is_file():
        raise RuntimeError(
            f"PA user-prompt missing for mode={mode!r}: expected {path}"
        )
    return path.read_text(encoding="utf-8").strip()


def _write_dry_run_summary(
    *,
    pa_dir: Path,
    mode: str,
    validated: Any,
    project_root: Path,
) -> Path:
    """Write `dry-run-summary.md` describing what apply_decision *would* do.

    Triggered when `pa_apply=False`: PA already produced a validated
    decision but the orchestrator skips writing new vNNNN. The summary
    is for the human reviewing the prompt: which units would have been
    bumped, to which version, with which deps, and (for world_*) which
    units would have been created and whether the baseline would advance.
    """
    lines: list[str] = []
    lines.append(f"# PA dry-run summary (mode={mode})")
    lines.append("")
    lines.append(
        "`PA_APPLY=0` — orchestrator validated the decision but did NOT "
        "write new versions, advance baseline, or append to registry."
    )
    lines.append("")

    changes = getattr(validated, "changes", None) or []
    if changes:
        lines.append("## Would refresh / bump existing units")
        lines.append("")
        lines.append("| unit_id | base_version | next_version | no_semantic_change | deps |")
        lines.append("|---------|--------------|--------------|--------------------|------|")
        for ch in changes:
            next_num = store.next_version_num(project_root, ch.unit_id)
            next_ver = store.format_version(next_num)
            dep_str = ", ".join(
                f"`{d.get('kind')}:{d.get('path')}`"
                for d in (ch.dependencies or [])
            ) or "(none)"
            lines.append(
                f"| `{ch.unit_id}` | `{ch.base_version}` | `{next_ver}` "
                f"| {ch.no_semantic_change} | {dep_str} |"
            )
        lines.append("")

    changes_refresh = getattr(validated, "changes_refresh", None) or []
    if changes_refresh:
        lines.append("## Would refresh existing BPs")
        lines.append("")
        lines.append("| unit_id | base_version | next_version | no_semantic_change | deps |")
        lines.append("|---------|--------------|--------------|--------------------|------|")
        for ch in changes_refresh:
            next_num = store.next_version_num(project_root, ch.unit_id)
            next_ver = store.format_version(next_num)
            dep_str = ", ".join(
                f"`{d.get('kind')}:{d.get('path')}`"
                for d in (ch.dependencies or [])
            ) or "(none)"
            lines.append(
                f"| `{ch.unit_id}` | `{ch.base_version}` | `{next_ver}` "
                f"| {ch.no_semantic_change} | {dep_str} |"
            )
        lines.append("")

    changes_new = getattr(validated, "changes_new", None) or []
    if changes_new:
        lines.append("## Would create new units")
        lines.append("")
        lines.append("| unit_id | kind | render_to | registry_position | deps |")
        lines.append("|---------|------|-----------|-------------------|------|")
        for nu in changes_new:
            dep_str = ", ".join(
                f"`{d.get('kind')}:{d.get('path')}`"
                for d in (nu.dependencies or [])
            ) or "(none)"
            lines.append(
                f"| `{nu.unit_id}` | {nu.kind} | `{nu.render_to}` "
                f"| `{nu.registry_position}` | {dep_str} |"
            )
        lines.append("")

    advance = getattr(validated, "advance_baseline", None)
    baseline_version = getattr(validated, "baseline_version", None)
    if advance is not None or baseline_version:
        lines.append("## Baseline")
        lines.append("")
        if baseline_version:
            lines.append(f"- current baseline_version: `{baseline_version}`")
        if advance is not None:
            lines.append(f"- would advance baseline: **{advance}**")
        lines.append("")

    unchanged = getattr(validated, "unchanged", None) or []
    if unchanged:
        lines.append(f"## Unchanged ({len(unchanged)})")
        lines.append("")
        for un in unchanged:
            uid = un.get("unit_id") if isinstance(un, dict) else None
            why = un.get("why") if isinstance(un, dict) else None
            if uid:
                lines.append(f"- `{uid}` — {why or ''}")
        lines.append("")

    path = pa_dir / "dry-run-summary.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _snapshot_rel(kind: str, path: str) -> str:
    if kind == "workspace":
        return "workspace/" + path.lstrip("/")
    if kind == "bin_help":
        return "bin-help/" + path
    if kind == "static":
        return "static/" + path
    if kind == "sql_table":
        return "sql-table/" + path.strip().lower() + ".schema.txt"
    raise ValueError(f"unknown dependency kind {kind!r}")


async def _execute_refresh(
    *, queue: PaQueue, job: PaJob, config: PaWorkerConfig
) -> PaJobResult:
    payload = job.payload
    pa_dir = Path(payload["pa_dir"])
    task_dir = Path(payload["task_dir"])
    unit_id = payload["unit_id"]
    base_version = payload["base_version"]
    # Materialise the workdir now, with a live read of `version-history/`.
    # If a concurrent failure_fix already published a newer version while
    # we were queued, that version shows up here.
    ref = store.get_version(config.project_root, unit_id, base_version)
    if ref is None:
        return PaJobResult(
            job_id=job.job_id,
            kind=job.kind,
            priority=PRIORITY_LABELS[job.priority],
            terminal_status="failed",
            duration_ms=0,
            pa_dir=str(pa_dir),
            error=(
                f"base_version {base_version!r} not found for unit "
                f"{unit_id!r} at PA-execute time"
            ),
        )
    manifest = store.load_manifest(ref)
    fp = FingerprintIndex(task_dir=task_dir, project_root=config.project_root)
    _materialise_refresh_workdir(
        project_root=config.project_root,
        pa_dir=pa_dir,
        task_id=payload.get("task_id", ""),
        trial_id=payload.get("trial_id", ""),
        unit_id=unit_id,
        ref=ref,
        manifest=manifest,
        fp=fp,
        task_dir=task_dir,
    )
    prompt = _read_user_prompt(config.project_root, "refresh")
    # Hold PA_LLM_CONCURRENCY only around the LLM call so deterministic
    # ingest below does not consume an LLM slot.
    async with queue.llm_slot(job.priority):
        spawn = await pa_runner.spawn_pa_cli(
            pa_dir=pa_dir,
            claude_bin=config.claude_bin,
            model=config.model,
            effort=config.effort,
            max_turns=config.max_turns,
            overall_timeout_sec=config.timeout_sec,
            user_prompt=prompt,
            label=job.job_id,
        )
    return await _ingest_pa_output(
        queue=queue,
        job=job,
        config=config,
        pa_dir=pa_dir,
        spawn=spawn,
        expected_mode="refresh",
        allowed_unit_ids=set(job.unit_ids),
        trigger={
            "task_id": payload.get("task_id"),
            "trial_id": payload.get("trial_id"),
            "unit_id": payload.get("unit_id"),
            "base_version": payload.get("base_version"),
            "pa_dir": str(pa_dir),
            "queue_priority": PRIORITY_LABELS[job.priority],
        },
    )


# ── Failure-fix ──────────────────────────────────────────────────────────


def queue_failure_fix(
    *,
    project_root: Path,
    failed_task_dir: Path,
    task_id: str,
    trial_id: str,
    instruction: str,
    score: float | None,
    score_detail: list[str],
    answer_outcome: str,
    pa_queue: PaQueue,
    label: str = "",
    mode: str = "failure_fix",
) -> tuple[asyncio.Future[PaJobResult], Path, list[str]]:
    """Queue a fix / fix_blind PA job without materialising the workdir.

    `mode` is `"failure_fix"` (open eval) or `"fix_blind"` (blind eval).
    The workdir is built lazily when the PA slot opens, so the
    `version-history/` snapshot reflects whatever other PAs have
    published while this job was queued. `selected_units` is not known
    until materialise time — ingest falls back to the full registry id
    set when `allowed_unit_ids` is None.
    """
    suffix = "" if mode == "failure_fix" else "-blind"
    pa_dir = (
        failed_task_dir.parent / f"{failed_task_dir.name}-process-architect{suffix}"
    )
    payload = {
        "project_root": str(project_root),
        "pa_dir": str(pa_dir),
        "failed_task_dir": str(failed_task_dir),
        "task_id": task_id,
        "trial_id": trial_id,
        "instruction": instruction,
        "score": score,
        "score_detail": score_detail,
        "answer_outcome": answer_outcome,
        "mode": mode,
    }
    future = pa_queue.submit_failure_fix(unit_ids=(), payload=payload, mode=mode)
    if label:
        print(f"{label} [PA] {mode} queued (workdir built at execute time)")
    return future, pa_dir, []


async def run_failure_fix(
    *,
    project_root: Path,
    failed_task_dir: Path,
    task_id: str,
    trial_id: str,
    instruction: str,
    score: float | None,
    score_detail: list[str],
    answer_outcome: str,
    pa_queue: PaQueue,
    label: str = "",
    mode: str = "failure_fix",
) -> PaJobResult:
    """Queue a fix / fix_blind PA job and await its terminal result."""
    future, _, _ = queue_failure_fix(
        project_root=project_root,
        failed_task_dir=failed_task_dir,
        task_id=task_id,
        trial_id=trial_id,
        instruction=instruction,
        score=score,
        score_detail=score_detail,
        answer_outcome=answer_outcome,
        pa_queue=pa_queue,
        label=label,
        mode=mode,
    )
    return await future


def _materialise_failure_fix_workdir(
    *,
    project_root: Path,
    failed_task_dir: Path,
    pa_dir: Path,
    task_id: str,
    trial_id: str,
    instruction: str,
    score: float | None,
    score_detail: list[str],
    answer_outcome: str,
    mode: str = "failure_fix",
) -> list[str]:
    if pa_dir.exists():
        shutil.rmtree(pa_dir)
    pa_dir.mkdir(parents=True)

    _copytree_filtered(
        failed_task_dir,
        pa_dir,
        skip_names={
            "__pycache__",
            ".mcp-config.json",
            "answer.json",
            "CLAUDE.md",  # we replace with PA's own
            "business_processes",  # we replace with selected-instructions/
        },
        skip_rel={
            ".logs/transcript.jsonl",
            ".logs/claude-stderr.log",
            ".logs/python",
        },
    )
    # Restore a clean answer.json copy at the workdir root.
    src_answer = failed_task_dir / "answer.json"
    if src_answer.is_file():
        shutil.copyfile(src_answer, pa_dir / "answer.json")

    # PA CLAUDE.md: self-contained failure_fix.md or fix_blind.md.
    prompts = store.pa_prompts_dir(project_root)
    (pa_dir / "CLAUDE.md").write_text(
        pa_runner.assemble_claude_md(prompts, mode=mode), encoding="utf-8"
    )
    pa_runner.write_pa_settings(pa_dir)

    # selected-instructions/ — what the Executor actually read.
    sel_root = pa_dir / "selected-instructions"
    sel_root.mkdir(parents=True, exist_ok=True)
    selection_path = failed_task_dir / ".logs" / "instruction-selection.json"
    selected: list[tuple[str, str]] = []  # (unit_id, version) pairs
    if selection_path.is_file():
        shutil.copyfile(
            selection_path, sel_root / "instruction-selection.json"
        )
        try:
            sel_data = json.loads(selection_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            sel_data = {}
        for u in sel_data.get("units") or []:
            uid = u.get("unit_id")
            version = u.get("selected_version")
            if not uid or not version:
                continue
            unit_target = sel_root / "units" / uid
            unit_target.mkdir(parents=True, exist_ok=True)
            (unit_target / "version.txt").write_text(version + "\n", encoding="utf-8")
            ref = store.get_version(project_root, uid, version)
            if ref is None:
                continue
            if ref.content_path.is_file():
                shutil.copyfile(ref.content_path, unit_target / "content.md")
            if ref.manifest_path.is_file():
                shutil.copyfile(ref.manifest_path, unit_target / "manifest.json")
            selected.append((uid, version))
    selected_units = [uid for uid, _ in selected]

    # version-history/ — full revision tree of every selected unit.
    _materialise_version_history(
        project_root=project_root,
        pa_dir=pa_dir,
        unit_ids=selected_units,
    )

    # vault/proc/ reconstruction from mcp-tool-calls.jsonl response payloads.
    _replay_proc_from_tool_calls(failed_task_dir=failed_task_dir, pa_dir=pa_dir)

    # failure-fix-task.md brief.
    is_blind = mode == "fix_blind"
    score_str = "N/A" if score is None else f"{score * 100:.1f}%"
    title_mode = "fix_blind" if is_blind else "failure-fix"
    lines = [
        f"# Process Architect {title_mode} — {task_id}",
        "",
        f"- trial_id: `{trial_id}`",
    ]
    if not is_blind:
        lines.append(f"- score: **{score_str}** (FAIL)")
    lines.append(f"- answer_outcome: `{answer_outcome}`")
    lines.append("")
    if not is_blind:
        lines.append("## Score detail (from get_trial)")
        lines.append("")
        if score_detail:
            lines.extend(f"- {item}" for item in score_detail)
        else:
            lines.append("- (no score_detail returned by the grader)")
    else:
        lines.append("## Score detail")
        lines.append("")
        lines.append(
            "(blind eval — neither score nor score_detail was returned by "
            "the grader; diagnose from the Executor trace alone)"
        )
    lines.extend(
        [
            "",
            "## Original task instruction",
            "",
            "```",
            instruction.strip(),
            "```",
            "",
            "## Selected unit versions (use as `base_version` per change)",
            "",
        ]
    )
    if selected:
        lines.extend(f"- `{uid}` → `{version}`" for uid, version in selected)
    else:
        lines.append("- (no instruction-selection.json found)")
    lines.extend(
        [
            "",
            "## Where to look",
            "",
            "1. `.logs/executor_actions.md` — snippet + tool-call digest.",
            "2. `scratchpad.json`, `state.json` — Executor's final state.",
            "3. `answer.json` — Executor's submission.",
            "4. `selected-instructions/units/<unit_id>/` — versions the",
            "   Executor read this trial.",
            "5. `version-history/units/<unit_id>/v*/` — full revision tree of",
            "   every selected unit (content.md, manifest.json, changes.md,",
            "   diff.patch). Read prior `changes.md` before re-adding a rule.",
            "6. `version-history/registry.json` — full unit roster and kinds.",
            "7. `version-history/prompts/process_architect/` — your own source",
            "   prompt fragments (the mode-specific `failure_fix.md` etc.).",
            "8. `vault/`, `bin-help/` — workspace snapshot at trial time. The",
            "   `/proc/<...>.json` records the Executor read are reconstructed",
            "   under `vault/proc/` from the audit log (best-effort).",
            "",
            "## Output",
            "",
            "Write `pa-output/pa-decision.json` per CLAUDE.md and one",
            "`pa-output/units/<unit_id>/content.md` per changed unit. The",
            "orchestrator will materialise new versions atomically.",
            "",
        ]
    )
    (pa_dir / "failure-fix-task.md").write_text("\n".join(lines), encoding="utf-8")

    (pa_dir / "pa-output").mkdir(parents=True, exist_ok=True)
    return selected_units


def _copytree_filtered(
    src: Path,
    dest: Path,
    *,
    skip_names: set[str],
    skip_rel: set[str] | None = None,
    _rel_prefix: str = "",
) -> None:
    skip_rel = skip_rel or set()
    dest.mkdir(parents=True, exist_ok=True)
    for entry in sorted(src.iterdir()):
        if entry.name in skip_names:
            continue
        rel = f"{_rel_prefix}{entry.name}" if _rel_prefix else entry.name
        if rel in skip_rel:
            continue
        target = dest / entry.name
        if entry.is_dir():
            _copytree_filtered(
                entry,
                target,
                skip_names=skip_names,
                skip_rel=skip_rel,
                _rel_prefix=f"{rel}/",
            )
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(entry, target)


def _materialise_version_history(
    *,
    project_root: Path,
    pa_dir: Path,
    unit_ids: list[str],
) -> None:
    """Mirror the full revision tree of selected units into `version-history/`.

    Layout:

        version-history/
          registry.json
          prompts/process_architect/{common,failure_fix,refresh}.md
          units/<unit_id>/<vNNNN>/{content.md, manifest.json,
                                    changes.md, diff.patch}

    Skips `dependency_snapshot/` — heavy and low signal for PA (PA reasons
    about policy text, not its prior hex-snapshot; resolver owns snapshots).
    """
    hist_root = pa_dir / "version-history"
    hist_root.mkdir(parents=True, exist_ok=True)

    registry_src = store.registry_path(project_root)
    if registry_src.is_file():
        shutil.copyfile(registry_src, hist_root / "registry.json")

    prompts_src = store.pa_prompts_dir(project_root)
    prompts_dest = hist_root / "prompts" / "process_architect"
    prompts_dest.mkdir(parents=True, exist_ok=True)
    for name in (
        "failure_fix.md",
        "fix_blind.md",
        "refresh.md",
        "world_refresh.md",
        "world_create.md",
        "conflict.md",
        "bp_author_contract.md",
    ):
        src = prompts_src / name
        if src.is_file():
            shutil.copyfile(src, prompts_dest / name)

    for uid in unit_ids:
        for ref in store.list_versions(project_root, uid):
            ver_dest = hist_root / "units" / uid / ref.version
            ver_dest.mkdir(parents=True, exist_ok=True)
            for name in ("content.md", "manifest.json", "changes.md", "diff.patch"):
                src = ref.version_dir / name
                if src.is_file():
                    shutil.copyfile(src, ver_dest / name)


def _replay_proc_from_tool_calls(
    *,
    failed_task_dir: Path,
    pa_dir: Path,
) -> None:
    """Reconstruct `vault/proc/<...>.json` from ws.read response payloads.

    `workspace.py` records each `ws.read` audit row with the response
    embedded (`{"tool": "read", "path": "/proc/...", "response": {...}}`).
    We walk the audit log and rematerialise unique `/proc/` records under
    `pa_dir/vault/proc/`.

    Best-effort: trials that ran before workspace.py started embedding
    responses won't have a `response` key; nothing is written, no error.
    """
    tool_calls_path = failed_task_dir / ".logs" / "mcp-tool-calls.jsonl"
    if not tool_calls_path.is_file():
        return
    seen: set[str] = set()
    for line in tool_calls_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict) or obj.get("tool") != "read":
            continue
        path = obj.get("path")
        if not isinstance(path, str) or not path.startswith("/proc/"):
            continue
        if path in seen:
            continue
        response = obj.get("response")
        if not isinstance(response, dict):
            continue
        content = response.get("content")
        if not isinstance(content, str):
            continue
        seen.add(path)
        target = pa_dir / "vault" / path.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.write_text(content, encoding="utf-8")
        except OSError:
            pass


async def _execute_failure_fix(
    *, queue: PaQueue, job: PaJob, config: PaWorkerConfig, mode: str = "failure_fix"
) -> PaJobResult:
    payload = job.payload
    pa_dir = Path(payload["pa_dir"])
    failed_task_dir = Path(payload["failed_task_dir"])
    # Materialise the workdir now (was deferred from queue time). The
    # `version-history/` snapshot here reflects everything other PAs
    # have published while this job sat in the queue.
    _materialise_failure_fix_workdir(
        project_root=config.project_root,
        failed_task_dir=failed_task_dir,
        pa_dir=pa_dir,
        task_id=payload.get("task_id", ""),
        trial_id=payload.get("trial_id", ""),
        instruction=payload.get("instruction", ""),
        score=payload.get("score"),
        score_detail=payload.get("score_detail") or [],
        answer_outcome=payload.get("answer_outcome", ""),
        mode=mode,
    )
    prompt = _read_user_prompt(config.project_root, mode)
    async with queue.llm_slot(job.priority):
        spawn = await pa_runner.spawn_pa_cli(
            pa_dir=pa_dir,
            claude_bin=config.claude_bin,
            model=config.model,
            effort=config.effort,
            max_turns=config.max_turns,
            overall_timeout_sec=config.timeout_sec,
            user_prompt=prompt,
            label=job.job_id,
        )
    # failure_fix / fix_blind may change any unit the Executor saw —
    # pass None to let validate_decision fall back to the full registry
    # id set.
    return await _ingest_pa_output(
        queue=queue,
        job=job,
        config=config,
        pa_dir=pa_dir,
        spawn=spawn,
        expected_mode=mode,
        allowed_unit_ids=None,
        trigger={
            "task_id": payload.get("task_id"),
            "trial_id": payload.get("trial_id"),
            "score": payload.get("score"),
            "score_detail": payload.get("score_detail"),
            "answer_outcome": payload.get("answer_outcome"),
            "failed_task_dir": payload.get("failed_task_dir"),
            "pa_dir": str(pa_dir),
            "queue_priority": PRIORITY_LABELS[job.priority],
        },
    )


# ── Shared output ingest ─────────────────────────────────────────────────


async def _ingest_pa_output(
    *,
    queue: PaQueue,
    job: PaJob,
    config: PaWorkerConfig,
    pa_dir: Path,
    spawn: pa_runner.PaSpawnResult,
    expected_mode: str,
    allowed_unit_ids: set[str] | None,
    trigger: dict[str, Any],
) -> PaJobResult:
    priority_label = PRIORITY_LABELS[job.priority]
    # Pre-declared so `_finalise` can pick it up via closure. The conflict
    # loop appends per-retry entries; `_finalise` flushes the accumulator
    # to `conflict-history.json` on every exit path so report_PA.md sees
    # the same data whether the job completed cleanly or bailed out.
    conflict_history: list[dict[str, Any]] = []

    def _finalise(result: PaJobResult) -> PaJobResult:
        if conflict_history:
            try:
                (pa_dir / "conflict-history.json").write_text(
                    json.dumps({"retries": conflict_history}, indent=2) + "\n",
                    encoding="utf-8",
                )
            except OSError as exc:
                print(
                    f"{job.job_id} [PA] conflict-history.json writer failed: "
                    f"{exc!r}"
                )
        # report_PA.md is always best-effort: errors here must not mask
        # the real terminal status returned to the queue.
        try:
            write_pa_report(
                pa_dir=pa_dir,
                result=result,
                expected_mode=expected_mode,
                trigger=trigger,
            )
        except Exception as exc:
            print(f"{job.job_id} [PA] report_PA.md writer failed: {exc!r}")
        return result

    if spawn.error == "timeout":
        return _finalise(PaJobResult(
            job_id=job.job_id,
            kind=job.kind,
            priority=priority_label,
            terminal_status="timeout",
            duration_ms=spawn.duration_ms,
            pa_dir=str(pa_dir),
            exit_code=spawn.exit_code,
            error="claude CLI timeout",
        ))
    if spawn.error:
        return _finalise(PaJobResult(
            job_id=job.job_id,
            kind=job.kind,
            priority=priority_label,
            terminal_status="failed",
            duration_ms=spawn.duration_ms,
            pa_dir=str(pa_dir),
            exit_code=spawn.exit_code,
            error=spawn.error,
        ))

    # Build a fresh fingerprint index off the trial dump that lives next
    # to the PA workdir. For refresh: vault/bin-help/static are in the
    # originating task_dir (one level up). For failure_fix: vault and
    # bin-help were copied into the PA workdir itself.
    if expected_mode == "refresh":
        task_dir_for_fp = pa_dir.parent / _refresh_task_dir_name(pa_dir.name)
    else:
        task_dir_for_fp = pa_dir
    fp = FingerprintIndex(
        task_dir=task_dir_for_fp, project_root=config.project_root
    )

    registry = store.load_registry(config.project_root)
    registry_ids = {u.id for u in registry}
    world_sigs = world_baseline.world_dep_signatures(
        world_baseline.load_world_files(config.project_root)
    )
    validated = pa_decision.validate_decision(
        project_root=config.project_root,
        pa_dir=pa_dir,
        expected_mode=expected_mode,
        registry_unit_ids=registry_ids,
        allowed_unit_ids=allowed_unit_ids,
        fp=fp,
        world_sigs=world_sigs,
    )
    _log_stripped_world_deps(job.job_id, validated.stripped_world_deps)

    if not validated.accepted:
        pa_decision.write_rejected(
            pa_dir=pa_dir, mode=expected_mode, validated=validated
        )
        return _finalise(PaJobResult(
            job_id=job.job_id,
            kind=job.kind,
            priority=priority_label,
            terminal_status="rejected",
            duration_ms=spawn.duration_ms,
            pa_dir=str(pa_dir),
            exit_code=spawn.exit_code,
            error=f"{len(validated.errors)} validation error(s); see pa-output/rejected.json",
        ))

    if not config.pa_apply:
        _write_dry_run_summary(
            pa_dir=pa_dir,
            mode=expected_mode,
            validated=validated,
            project_root=config.project_root,
        )
        print(
            f"{job.job_id} [PA] PA_APPLY=0 — dry-run; "
            f"{len(validated.changes)} change(s) validated but not applied"
        )
        return _finalise(PaJobResult(
            job_id=job.job_id,
            kind=job.kind,
            priority=priority_label,
            terminal_status="dry_run_completed",
            duration_ms=spawn.duration_ms,
            pa_dir=str(pa_dir),
            exit_code=spawn.exit_code,
        ))

    # ── Apply + conflict retry loop ──
    # apply_decision returns both written versions and any stale-base
    # conflicts. If conflict mode is enabled and retries remain, we
    # respawn PA with conflict.md and rebase the failing changes onto
    # the new latest. Loop terminates on no-conflict, retry exhaustion,
    # or PA rejection of the rebased decision.
    accumulated_spawn_ms = spawn.duration_ms
    conflict_retries = 0
    # Accumulator: versions successfully written across ALL iterations.
    # apply_result.written only holds the LAST iteration's writes, so we
    # extend here to preserve writes from earlier passes (non-conflicted
    # units applied in pass 1 must not vanish from the final report).
    all_written: list[versioning.WrittenVersion] = []
    while True:
        apply_result = await pa_decision.apply_decision(
            project_root=config.project_root,
            validated=validated,
            fp=fp,
            trigger=trigger,
            pa_queue=queue,
            label=job.job_id,
        )
        all_written.extend(apply_result.written)
        if not apply_result.stale_conflicts:
            break
        if not config.conflict_mode:
            print(
                f"{job.job_id} [PA] {len(apply_result.stale_conflicts)} stale "
                "base(s) but PA_CONFLICT_MODE=disabled — silent fork(s) written"
            )
            break
        if conflict_retries >= config.conflict_max_retries:
            print(
                f"{job.job_id} [PA] stale-base conflict, retries exhausted "
                f"({conflict_retries}/{config.conflict_max_retries})"
            )
            return _finalise(PaJobResult(
                job_id=job.job_id,
                kind=job.kind,
                priority=priority_label,
                terminal_status="conflict_unresolved",
                duration_ms=accumulated_spawn_ms,
                pa_dir=str(pa_dir),
                exit_code=spawn.exit_code,
                error=(
                    f"{len(apply_result.stale_conflicts)} stale base "
                    "conflict(s) after max retries"
                ),
                created_versions=[
                    {"unit_id": w.unit_id, "version": w.version}
                    for w in all_written
                ],
            ))
        # Rebase: materialise conflict context, re-spawn PA in conflict mode.
        conflict_retries += 1
        conflict_history.append({
            "retry": conflict_retries,
            "conflicts": [
                {
                    "unit_id": c.unit_id,
                    "original_base": c.original_base,
                    "current_latest": c.current_latest,
                }
                for c in apply_result.stale_conflicts
            ],
            "partial_written": [
                {"unit_id": w.unit_id, "version": w.version}
                for w in apply_result.written
            ],
        })
        print(
            f"{job.job_id} [PA] conflict retry {conflict_retries}/"
            f"{config.conflict_max_retries} for "
            f"{[c.unit_id for c in apply_result.stale_conflicts]}"
        )
        _materialise_conflict_context(
            project_root=config.project_root,
            pa_dir=pa_dir,
            conflicts=apply_result.stale_conflicts,
            retry_num=conflict_retries,
        )
        rebase_prompt = _read_user_prompt(
            config.project_root, "conflict"
        ).replace("{n}", f"{conflict_retries:02d}")
        async with queue.llm_slot(job.priority):
            retry_spawn = await pa_runner.spawn_pa_cli(
                pa_dir=pa_dir,
                claude_bin=config.claude_bin,
                model=config.model,
                effort=config.effort,
                max_turns=config.max_turns,
                overall_timeout_sec=config.timeout_sec,
                user_prompt=rebase_prompt,
                label=f"{job.job_id}-conflict-{conflict_retries}",
            )
        accumulated_spawn_ms += retry_spawn.duration_ms
        if retry_spawn.error:
            return _finalise(PaJobResult(
                job_id=job.job_id,
                kind=job.kind,
                priority=priority_label,
                terminal_status="conflict_unresolved",
                duration_ms=accumulated_spawn_ms,
                pa_dir=str(pa_dir),
                exit_code=retry_spawn.exit_code,
                error=f"conflict retry spawn failed: {retry_spawn.error}",
                created_versions=[
                    {"unit_id": w.unit_id, "version": w.version}
                    for w in all_written
                ],
            ))
        # Conflict-retry validation:
        # - empty `changes[]` allowed (all conflicted units subsumed).
        # - `expected_conflict_units` triggers coverage check: every unit
        #   in conflict MUST land in either `changes[]` (with
        #   `conflict_resolution`) or `subsumed[]` (with rationale).
        conflict_unit_set = {c.unit_id for c in apply_result.stale_conflicts}
        validated = pa_decision.validate_decision(
            project_root=config.project_root,
            pa_dir=pa_dir,
            expected_mode=expected_mode,
            registry_unit_ids=registry_ids,
            allowed_unit_ids=allowed_unit_ids,
            fp=fp,
            world_sigs=world_sigs,
            allow_empty_changes=True,
            expected_conflict_units=conflict_unit_set,
        )
        if not validated.accepted:
            pa_decision.write_rejected(
                pa_dir=pa_dir, mode=expected_mode, validated=validated
            )
            return _finalise(PaJobResult(
                job_id=job.job_id,
                kind=job.kind,
                priority=priority_label,
                terminal_status="conflict_unresolved",
                duration_ms=accumulated_spawn_ms,
                pa_dir=str(pa_dir),
                exit_code=retry_spawn.exit_code,
                error=(
                    f"conflict retry validation failed: "
                    f"{len(validated.errors)} error(s); see "
                    "pa-output/rejected.json"
                ),
                created_versions=[
                    {"unit_id": w.unit_id, "version": w.version}
                    for w in all_written
                ],
            ))
        # The next loop iteration re-applies the rebased decision under
        # fresh locks; `all_written` accumulates results across passes.

    created = [
        {"unit_id": w.unit_id, "version": w.version}
        for w in all_written
    ]
    # conflict-history.json is flushed by _finalise on every exit path.
    return _finalise(PaJobResult(
        job_id=job.job_id,
        kind=job.kind,
        priority=priority_label,
        terminal_status="completed",
        duration_ms=accumulated_spawn_ms,
        pa_dir=str(pa_dir),
        exit_code=spawn.exit_code,
        created_versions=created,
    ))


def _log_stripped_world_deps(
    label: str, stripped: list[dict[str, Any]]
) -> None:
    """Log when validator silently dropped PA-pinned world-deps.

    PA prompts intentionally do NOT carry the world-list membership rule
    (it would add load for a problem the validator can fix mechanically).
    When PA still pins a world file, validator strips it and we log here
    so ops can spot the pattern (e.g. if a particular failure mode keeps
    triggering it).
    """
    if not stripped:
        return
    summary = ", ".join(
        f"{s['unit_id']}:{s['kind']}:{s['path']}" for s in stripped
    )
    print(
        f"{label} [PA] stripped {len(stripped)} world-dep(s) from PA decision: {summary}"
    )


def _refresh_task_dir_name(pa_dir_name: str) -> str:
    """Reverse the convention `<task_dir.name>-process-architect-refresh-<unit_id>`."""
    marker = "-process-architect-refresh-"
    idx = pa_dir_name.find(marker)
    if idx < 0:
        return pa_dir_name
    return pa_dir_name[:idx]


def _world_refresh_task_dir_name(pa_dir_name: str) -> str:
    """Reverse `<task_dir.name>-process-architect-world-{refresh,create}-<key>`."""
    for marker in (
        "-process-architect-world-refresh-",
        "-process-architect-world-create-",
    ):
        idx = pa_dir_name.find(marker)
        if idx >= 0:
            return pa_dir_name[:idx]
    return pa_dir_name


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ── World refresh ────────────────────────────────────────────────────────


# ── World create (operator-invoked sibling of world_refresh) ─────────────


_WORLD_CREATE_SEED_KEY = "seed"


async def enqueue_async_world_create(
    *,
    task_dir: Path,
    task_id: str,
    trial_id: str,
    baseline_ref: Any,  # may be None for empty-baseline seed run
    drift: list[Any],
    pa_queue: PaQueue,
    label: str = "",
) -> dict[str, Any]:
    """Submit world_create at async priority. Workdir built at execute time."""
    suffix, baseline_version = (
        (baseline_ref.version, baseline_ref.version)
        if baseline_ref is not None
        else (_WORLD_CREATE_SEED_KEY, _WORLD_CREATE_SEED_KEY)
    )
    pa_dir = task_dir.parent / (
        f"{task_dir.name}-process-architect-world-create-{suffix}"
    )
    payload = {
        "pa_dir": str(pa_dir),
        "task_dir": str(task_dir),
        "task_id": task_id,
        "trial_id": trial_id,
        "baseline_version": baseline_version,
    }
    _, is_new = pa_queue.submit_world_create(
        baseline_version=baseline_version,
        payload=payload,
        priority=PRIORITY_WORLD_REFRESH,
    )
    if label:
        kind_suffix = "new" if is_new else "joined existing"
        print(
            f"{label} [resolver] queued world_create for baseline "
            f"{baseline_version} ({kind_suffix}); drift={len(drift)} files"
        )
    return {
        "baseline_version": baseline_version,
        "queue_priority": PRIORITY_LABELS[PRIORITY_WORLD_REFRESH],
        "waited": False,
        "is_new_job": is_new,
        "drift_count": len(drift),
    }


async def run_world_create_blocking(
    *,
    task_dir: Path,
    task_id: str,
    trial_id: str,
    baseline_ref: Any,
    drift: list[Any],
    pa_queue: PaQueue,
    label: str = "",
) -> dict[str, Any]:
    """Submit world_create at blocking priority, await terminal result."""
    suffix, baseline_version = (
        (baseline_ref.version, baseline_ref.version)
        if baseline_ref is not None
        else (_WORLD_CREATE_SEED_KEY, _WORLD_CREATE_SEED_KEY)
    )
    pa_dir = task_dir.parent / (
        f"{task_dir.name}-process-architect-world-create-{suffix}"
    )
    payload = {
        "pa_dir": str(pa_dir),
        "task_dir": str(task_dir),
        "task_id": task_id,
        "trial_id": trial_id,
        "baseline_version": baseline_version,
    }
    future, is_new = pa_queue.submit_world_create(
        baseline_version=baseline_version,
        payload=payload,
        priority=PRIORITY_BLOCKING,
    )
    if label:
        print(
            f"{label} [resolver] awaiting world_create for baseline "
            f"{baseline_version} (is_new={is_new})"
        )
    try:
        result = await future
    except BaseException as exc:
        return {
            "baseline_version": baseline_version,
            "queue_priority": PRIORITY_LABELS[PRIORITY_BLOCKING],
            "waited": True,
            "is_new_job": is_new,
            "drift_count": len(drift),
            "completion": {"terminal_status": "failed", "error": repr(exc)},
        }
    return {
        "baseline_version": baseline_version,
        "queue_priority": PRIORITY_LABELS[PRIORITY_BLOCKING],
        "waited": True,
        "is_new_job": is_new,
        "drift_count": len(drift),
        "completion": {
            "terminal_status": result.terminal_status,
            "new_baseline": result.new_baseline,
            "created_versions": result.created_versions,
            "created_units": result.created_units,
            "error": result.error,
        },
    }


async def _execute_world_create(
    *, queue: PaQueue, job: PaJob, config: PaWorkerConfig
) -> PaJobResult:
    payload = job.payload
    pa_dir = Path(payload["pa_dir"])
    task_dir = Path(payload["task_dir"])
    baseline_version = payload.get("baseline_version") or _WORLD_CREATE_SEED_KEY

    # Seed mode (no parent baseline yet) vs advance-from-existing.
    baseline_ref = (
        None
        if baseline_version == _WORLD_CREATE_SEED_KEY
        else world_baseline.get_baseline(config.project_root, baseline_version)
    )
    fp = FingerprintIndex(task_dir=task_dir, project_root=config.project_root)
    baseline_manifest = (
        world_baseline.load_baseline_manifest(baseline_ref)
        if baseline_ref is not None
        else None
    )
    # Effective set = explicit world.json + auto-discovered /bin tool
    # surface (variant B); include the baseline so a removed tool still
    # surfaces as missing_in_current drift for the PA to see.
    world_files = world_baseline.effective_world_files(
        config.project_root, fp, baseline_manifest
    )
    drift = world_baseline.compute_drift(baseline_manifest, fp, world_files)

    _materialise_world_refresh_workdir(
        project_root=config.project_root,
        pa_dir=pa_dir,
        task_dir=task_dir,
        task_id=payload.get("task_id", ""),
        trial_id=payload.get("trial_id", ""),
        baseline_ref=baseline_ref,
        drift=drift,
        fp=fp,
        mode="world_create",
    )
    prompt = _read_user_prompt(config.project_root, "world_create")
    async with queue.llm_slot(job.priority):
        spawn = await pa_runner.spawn_pa_cli(
            pa_dir=pa_dir,
            claude_bin=config.claude_bin,
            model=config.model,
            effort=config.effort,
            max_turns=config.max_turns,
            overall_timeout_sec=config.world_timeout_sec,
            user_prompt=prompt,
            label=job.job_id,
        )
    return await _ingest_world_refresh_output(
        queue=queue,
        job=job,
        config=config,
        pa_dir=pa_dir,
        spawn=spawn,
        trigger={
            "task_id": payload.get("task_id"),
            "trial_id": payload.get("trial_id"),
            "baseline_version": baseline_version,
            "pa_dir": str(pa_dir),
            "queue_priority": PRIORITY_LABELS[job.priority],
            "mode": "world_create",
        },
        expected_mode="world_create",
    )


async def enqueue_async_world_refresh(
    *,
    task_dir: Path,
    task_id: str,
    trial_id: str,
    baseline_ref: Any,  # world_baseline.BaselineRef (signature/log only)
    drift: list[Any],   # list[world_baseline.DriftEntry] (count only)
    pa_queue: PaQueue,
    label: str = "",
) -> dict[str, Any]:
    """Submit world_refresh at async priority. Workdir built at execute time."""
    pa_dir = task_dir.parent / (
        f"{task_dir.name}-process-architect-world-refresh-{baseline_ref.version}"
    )
    payload = {
        "pa_dir": str(pa_dir),
        "task_dir": str(task_dir),
        "task_id": task_id,
        "trial_id": trial_id,
        "baseline_version": baseline_ref.version,
    }
    _, is_new = pa_queue.submit_world_refresh(
        baseline_version=baseline_ref.version,
        payload=payload,
        priority=PRIORITY_WORLD_REFRESH,
    )
    if label:
        kind_suffix = "new" if is_new else "joined existing"
        print(
            f"{label} [resolver] queued world_refresh for baseline "
            f"{baseline_ref.version} ({kind_suffix}); drift={len(drift)} files"
        )
    return {
        "baseline_version": baseline_ref.version,
        "queue_priority": PRIORITY_LABELS[PRIORITY_WORLD_REFRESH],
        "waited": False,
        "is_new_job": is_new,
        "drift_count": len(drift),
    }


async def run_world_refresh_blocking(
    *,
    task_dir: Path,
    task_id: str,
    trial_id: str,
    baseline_ref: Any,
    drift: list[Any],
    pa_queue: PaQueue,
    label: str = "",
) -> dict[str, Any]:
    """Submit at blocking priority, await terminal result. Workdir at execute time."""
    pa_dir = task_dir.parent / (
        f"{task_dir.name}-process-architect-world-refresh-{baseline_ref.version}"
    )
    payload = {
        "pa_dir": str(pa_dir),
        "task_dir": str(task_dir),
        "task_id": task_id,
        "trial_id": trial_id,
        "baseline_version": baseline_ref.version,
    }
    future, is_new = pa_queue.submit_world_refresh(
        baseline_version=baseline_ref.version,
        payload=payload,
        priority=PRIORITY_BLOCKING,
    )
    if label:
        print(
            f"{label} [resolver] awaiting world_refresh for baseline "
            f"{baseline_ref.version} (is_new={is_new})"
        )
    try:
        result = await future
    except BaseException as exc:  # pragma: no cover — defensive
        return {
            "baseline_version": baseline_ref.version,
            "queue_priority": PRIORITY_LABELS[PRIORITY_BLOCKING],
            "waited": True,
            "is_new_job": is_new,
            "drift_count": len(drift),
            "completion": {"terminal_status": "failed", "error": repr(exc)},
        }
    return {
        "baseline_version": baseline_ref.version,
        "queue_priority": PRIORITY_LABELS[PRIORITY_BLOCKING],
        "waited": True,
        "is_new_job": is_new,
        "drift_count": len(drift),
        "completion": {
            "terminal_status": result.terminal_status,
            "new_baseline": result.new_baseline,
            "created_versions": result.created_versions,
            "created_units": result.created_units,
            "error": result.error,
        },
    }


def _build_dep_index(project_root: Path) -> dict[str, list[str]]:
    """Map each dependency path → BP unit ids that currently pin it.

    Scans the latest *active* version of every registered unit. `workspace`
    deps key on `/docs/...`, `bin_help` on the bare filename, `sql_table` on the
    table name — the same forms `world-changes.md` looks up. Fills the "grounds
    units" column so the PA sees which BPs a changed path most likely affects.
    """
    idx: dict[str, list[str]] = {}
    for reg in store.load_registry(project_root):
        active = [
            v
            for v in store.list_versions(project_root, reg.id)
            if store.load_manifest(v).status == store.STATUS_ACTIVE
        ]
        if not active:
            continue
        for dep in store.load_manifest(active[-1]).dependencies:
            idx.setdefault(dep.path, []).append(reg.id)
    return idx


def _materialise_world_refresh_workdir(
    *,
    project_root: Path,
    pa_dir: Path,
    task_dir: Path,
    task_id: str,
    trial_id: str,
    baseline_ref: Any,
    drift: list[Any],
    fp: FingerprintIndex,
    mode: str = "world_refresh",
) -> None:
    """Schema-v2 layout (task-022 §6.3 / §6.2):

        <pa_dir>/
          CLAUDE.md
          bin-help/                       # mirror task_dir/bin-help/
          bin-help-diff.patch             # FULL bin-help diff (tool surface + schema)
          world-changes.md                # vault triage index (baseline → live)
          world-edits.patch               # LEAN patch: surgical vault deltas only
          relocations.json                # machine-readable file-set map
          pa-output/                      # PA writes here
          processes/
            active/<bp_id>/{content.md, manifest.json}
            drafts/<bp_id>.md             # populated in stage 6
            author-contract.md
            inventory.md
            registry.json
          vault/                          # mirror task_dir/vault/
          .claude/settings.json           # out-of-band
    """
    if pa_dir.exists():
        shutil.rmtree(pa_dir)
    pa_dir.mkdir(parents=True)

    prompts = store.pa_prompts_dir(project_root)
    (pa_dir / "CLAUDE.md").write_text(
        pa_runner.assemble_claude_md(prompts, mode=mode),
        encoding="utf-8",
    )
    pa_runner.write_pa_settings(pa_dir)

    # vault/ + bin-help/ — full mirrors of the trial dump.
    vault_src = task_dir / "vault"
    if vault_src.is_dir():
        shutil.copytree(vault_src, pa_dir / "vault", dirs_exist_ok=True)
    bin_help_src = task_dir / "bin-help"
    if bin_help_src.is_dir():
        shutil.copytree(bin_help_src, pa_dir / "bin-help", dirs_exist_ok=True)

    # Rule-4 proc samples live under the trial's `.logs/` (executor-invisible,
    # pre-bootstrap v4). The world_refresh/world_create prompts read them at
    # `vault/proc/<family>/__sample__.json`, so graft the `proc/` subtree into
    # the PA's vault here — they exist for these modes only.
    samples_proc = world_samples_dir(task_dir) / "proc"
    if samples_proc.is_dir():
        shutil.copytree(samples_proc, pa_dir / "vault" / "proc", dirs_exist_ok=True)

    # Baseline subtree roots, compared FRESH against the current trial dump
    # (not the baseline's stored v(N-1)→vN diff): the PA needs baseline → live
    # (task-022 plan §6.3). For an absent baseline (world_create seed) both
    # sides are empty/None.
    bl_vault = baseline_ref.version_dir / "vault" if baseline_ref else None
    bl_bin_help = (
        baseline_ref.snapshot_dir / "bin-help" if baseline_ref else None
    )
    bl_version = baseline_ref.version if baseline_ref else "empty"

    # bin-help-diff.patch — the tool/command surface + SQL schema. This is
    # high-signal REFERENCE data (the PA's Schema and Capability ledgers read
    # it): "table X added, column Y added, new verb Z" — the DELTA is the
    # signal even when large, and reading the whole schema live would not show
    # what changed. So bin-help keeps a dedicated FULL diff — no rewrite-floor,
    # never collapsed to "read live". bin-help is small and rarely renames, so
    # a plain tree diff stays compact (it was never part of the vault-diff
    # bloat).
    (pa_dir / "bin-help-diff.patch").write_text(
        world_baseline.diff_trees(
            old_root=bl_bin_help,
            new_root=task_dir / "bin-help",
            old_label=f"baseline-{bl_version}/bin-help",
            new_label="bin-help",
            exclude_json=False,
        ),
        encoding="utf-8",
    )

    # world-changes.md + world-edits.patch — the VAULT change view
    # (docs/proc/run/AGENTS) only. A plain vault diff is ~90% rename delete/add
    # noise, dumps every new file, and turns a doc rewrite into a giant useless
    # delta. So we pair renames (SHA256 + token similarity, `detect_relocations`)
    # then reorganise (`build_world_changes`) into a triage index
    # (`world-changes.md`, incl. a "grounds units" column from the dep index)
    # plus a LEAN patch (`world-edits.patch`) holding ONLY surgical content
    # deltas; pure renames, new/removed files, and full rewrites are listed for
    # read-live, never dumped. bin-help is NOT folded in here — it has its own
    # full diff above. `relocations.json` keeps the machine-readable rename map
    # across BOTH trees. `__sample__.json` fixtures are skipped.
    vault_reloc = world_baseline.detect_relocations(
        bl_vault, task_dir / "vault", rel_prefix="vault/"
    )
    binhelp_reloc = world_baseline.detect_relocations(
        bl_bin_help, task_dir / "bin-help", rel_prefix="bin-help/"
    )
    # Drop `added` files that nothing references (e.g. dated policy-update
    # distractors discovered by rule, not by link) so they aren't surfaced as
    # "new files" to the PA either — same reachability rule as the executor.
    current_trees = [
        (task_dir / "vault", "vault/"),
        (task_dir / "bin-help", "bin-help/"),
    ]
    vault_reloc = world_baseline.prune_unreferenced_added(
        vault_reloc, current_trees=current_trees
    )
    binhelp_reloc = world_baseline.prune_unreferenced_added(
        binhelp_reloc, current_trees=current_trees
    )
    reloc_report = world_baseline.merge_relocation_reports(
        [vault_reloc, binhelp_reloc]
    )
    changeset = world_baseline.build_world_changes(
        trees=[(bl_vault, task_dir / "vault", "vault/", True)],
        reloc_report=vault_reloc,
    )
    (pa_dir / "world-changes.md").write_text(
        world_baseline.render_world_changes_md(
            changeset,
            project_root=project_root,
            dep_index=_build_dep_index(project_root),
        ),
        encoding="utf-8",
    )
    (pa_dir / "world-edits.patch").write_text(
        world_baseline.render_world_edits_patch(changeset), encoding="utf-8"
    )
    (pa_dir / "relocations.json").write_text(
        json.dumps(world_baseline.relocations_payload(reloc_report), indent=2)
        + "\n",
        encoding="utf-8",
    )

    # processes/ — author-contract, inventory, registry, active snapshots,
    # drafts (filled in stage 6 once units_draft/ exists).
    proc_dir = pa_dir / "processes"
    (proc_dir / "active").mkdir(parents=True, exist_ok=True)
    (proc_dir / "drafts").mkdir(parents=True, exist_ok=True)

    contract_src = prompts / "bp_author_contract.md"
    if contract_src.is_file():
        shutil.copyfile(contract_src, proc_dir / "author-contract.md")

    registry_src = store.registry_path(project_root)
    if registry_src.is_file():
        shutil.copyfile(registry_src, proc_dir / "registry.json")

    (proc_dir / "inventory.md").write_text(
        _render_bps_inventory(project_root), encoding="utf-8"
    )

    # processes/active/<unit_id>/{content.md, manifest.json}
    # Latest active version per registered unit. Includes executor_core
    # so PA can see — but mustn't edit — it; the prompt explicitly
    # excludes executor_core from world_refresh edits.
    for reg in store.load_registry(project_root):
        refs = store.list_versions(project_root, reg.id)
        if not refs:
            continue
        active = [
            r for r in refs if store.load_manifest(r).status == store.STATUS_ACTIVE
        ]
        latest = active[-1] if active else refs[-1]
        unit_target = proc_dir / "active" / reg.id
        unit_target.mkdir(parents=True, exist_ok=True)
        if latest.content_path.is_file():
            shutil.copyfile(latest.content_path, unit_target / "content.md")
        if latest.manifest_path.is_file():
            shutil.copyfile(latest.manifest_path, unit_target / "manifest.json")

    # processes/drafts/ — populated by stage 6 (units_draft/ feature).
    _materialise_drafts(project_root=project_root, pa_dir=pa_dir)

    (pa_dir / "pa-output").mkdir(parents=True, exist_ok=True)

    # `drift`, `task_id`, `trial_id`, `fp` are intentionally NOT surfaced
    # as build-time files — per task-022 §6.3, PA reads CLAUDE.md and the
    # two concat-diffs; no brief, no version-history. Audit context goes
    # into post-run `report_PA.md` + `pa-result.json` (see §6.1).
    _ = drift, task_id, trial_id, fp


def _materialise_drafts(*, project_root: Path, pa_dir: Path) -> None:
    """Copy `agent/instructions/units_draft/*.md` into `processes/drafts/`.

    Best-effort: when `units_draft/` is absent (pre-stage-6) the dir
    stays empty. Per task-022 §8 drafts are not registered in
    `registry.json`; PA must decide their fate (`ground` / `merge` /
    `prune` / `keep`) and only the grounded ones get appended to the
    registry on apply.
    """
    src_dir = store.instructions_dir(project_root) / "units_draft"
    if not src_dir.is_dir():
        return
    dst_dir = pa_dir / "processes" / "drafts"
    dst_dir.mkdir(parents=True, exist_ok=True)
    for entry in sorted(src_dir.iterdir()):
        if entry.is_file() and entry.suffix.lower() == ".md":
            shutil.copyfile(entry, dst_dir / entry.name)


def _world_baseline_module():
    """Lazy import to avoid circular dependency at module load time."""
    from . import world_baseline
    return world_baseline


def _render_bps_inventory(project_root: Path) -> str:
    """Build `current-bps-inventory.md` from registry + latest manifests."""
    registry = store.load_registry(project_root)
    world_baseline_mod = _world_baseline_module()
    world_sigs = world_baseline_mod.world_dep_signatures(
        world_baseline_mod.load_world_files(project_root)
    )
    from .fingerprints import normalize as _normalize

    lines: list[str] = [
        "# Current BP inventory",
        "",
        "Every registered unit (executor_prompt + business_process). Use",
        "this to decide what to refresh, what to extend, what to leave as",
        "unchanged, and which existing BP is closest to a new candidate.",
        "",
        "| unit_id | kind | render_to | latest_version | summary | non-world deps |",
        "|---------|------|-----------|----------------|---------|----------------|",
    ]
    for reg in registry:
        refs = store.list_versions(project_root, reg.id)
        if not refs:
            lines.append(
                f"| `{reg.id}` | {reg.kind} | `{reg.render_to}` | (none) | (no versions) | (n/a) |"
            )
            continue
        # latest active wins; fall back to absolute latest if none active
        active = [r for r in refs if store.load_manifest(r).status == store.STATUS_ACTIVE]
        latest = active[-1] if active else refs[-1]
        try:
            manifest = store.load_manifest(latest)
        except Exception:
            manifest = None
        summary = _first_meaningful_line(latest.content_path) if latest.content_path.is_file() else "(content missing)"
        deps_str = "(none)"
        if manifest is not None:
            non_world = [
                d for d in manifest.dependencies
                if (d.kind, _normalize(d.kind, d.path)) not in world_sigs
            ]
            if non_world:
                deps_str = ", ".join(f"`{d.kind}:{d.path}`" for d in non_world)
        lines.append(
            f"| `{reg.id}` | {reg.kind} | `{reg.render_to}` | "
            f"`{latest.version}` | {summary} | {deps_str} |"
        )
    return "\n".join(lines) + "\n"


def _first_meaningful_line(content_path: Path) -> str:
    """First non-empty non-heading line, escaped for a markdown table cell."""
    try:
        text = content_path.read_text(encoding="utf-8")
    except OSError:
        return "(unreadable)"
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        if line.startswith(">"):
            # Skip blockquote stale warnings.
            continue
        # Escape pipes for markdown table.
        return line.replace("|", "\\|")[:120]
    return "(empty)"


# `_render_workspace_tree`, `_walk_tree`, and `_materialise_baseline_history`
# were retired in task-022 stage 5 — the new world_refresh workdir lets PA
# read `vault/` and `bin-help/` directly and intentionally hides
# `version-history/`.


async def _execute_world_refresh(
    *, queue: PaQueue, job: PaJob, config: PaWorkerConfig
) -> PaJobResult:
    payload = job.payload
    pa_dir = Path(payload["pa_dir"])
    task_dir = Path(payload["task_dir"])
    baseline_version = payload["baseline_version"]
    # Materialise workdir now — recompute drift against current trial
    # dump (task_dir/vault is immutable after bootstrap).
    baseline_ref = world_baseline.get_baseline(config.project_root, baseline_version)
    if baseline_ref is None:
        return PaJobResult(
            job_id=job.job_id,
            kind=job.kind,
            priority=PRIORITY_LABELS[job.priority],
            terminal_status="failed",
            duration_ms=0,
            pa_dir=str(pa_dir),
            error=f"baseline {baseline_version!r} not found at PA-execute time",
        )
    baseline_manifest = world_baseline.load_baseline_manifest(baseline_ref)
    fp = FingerprintIndex(task_dir=task_dir, project_root=config.project_root)
    # Effective set (variant B): explicit world.json + auto-discovered /bin
    # tool surface, with the baseline pooled in so a removed tool still
    # shows as missing_in_current drift.
    world_files = world_baseline.effective_world_files(
        config.project_root, fp, baseline_manifest
    )
    drift = world_baseline.compute_drift(baseline_manifest, fp, world_files)
    _materialise_world_refresh_workdir(
        project_root=config.project_root,
        pa_dir=pa_dir,
        task_dir=task_dir,
        task_id=payload.get("task_id", ""),
        trial_id=payload.get("trial_id", ""),
        baseline_ref=baseline_ref,
        drift=drift,
        fp=fp,
    )
    prompt = _read_user_prompt(config.project_root, "world_refresh")
    async with queue.llm_slot(job.priority):
        spawn = await pa_runner.spawn_pa_cli(
            pa_dir=pa_dir,
            claude_bin=config.claude_bin,
            model=config.model,
            effort=config.effort,
            max_turns=config.max_turns,
            overall_timeout_sec=config.world_timeout_sec,
            user_prompt=prompt,
            label=job.job_id,
        )
    return await _ingest_world_refresh_output(
        queue=queue,
        job=job,
        config=config,
        pa_dir=pa_dir,
        spawn=spawn,
        trigger={
            "task_id": payload.get("task_id"),
            "trial_id": payload.get("trial_id"),
            "baseline_version": payload.get("baseline_version"),
            "pa_dir": str(pa_dir),
            "queue_priority": PRIORITY_LABELS[job.priority],
        },
    )


async def _ingest_world_refresh_output(
    *,
    queue: PaQueue,
    job: PaJob,
    config: PaWorkerConfig,
    pa_dir: Path,
    spawn: pa_runner.PaSpawnResult,
    trigger: dict[str, Any],
    expected_mode: str = "world_refresh",
) -> PaJobResult:
    priority_label = PRIORITY_LABELS[job.priority]

    def _finalise(result: PaJobResult) -> PaJobResult:
        try:
            write_pa_report(
                pa_dir=pa_dir,
                result=result,
                expected_mode=expected_mode,
                trigger=trigger,
            )
        except Exception as exc:
            print(f"{job.job_id} [PA] report_PA.md writer failed: {exc!r}")
        return result

    if spawn.error == "timeout":
        return _finalise(PaJobResult(
            job_id=job.job_id,
            kind=job.kind,
            priority=priority_label,
            terminal_status="timeout",
            duration_ms=spawn.duration_ms,
            pa_dir=str(pa_dir),
            exit_code=spawn.exit_code,
            error="claude CLI timeout",
        ))
    if spawn.error:
        return _finalise(PaJobResult(
            job_id=job.job_id,
            kind=job.kind,
            priority=priority_label,
            terminal_status="failed",
            duration_ms=spawn.duration_ms,
            pa_dir=str(pa_dir),
            exit_code=spawn.exit_code,
            error=spawn.error,
        ))

    # Fresh fingerprint index off the trial dump that triggered this job.
    task_dir_for_fp = pa_dir.parent / _world_refresh_task_dir_name(pa_dir.name)
    fp = FingerprintIndex(
        task_dir=task_dir_for_fp, project_root=config.project_root
    )

    registry = store.load_registry(config.project_root)
    registry_ids = {u.id for u in registry}
    bp_unit_ids = {u.id for u in registry if u.kind == "business_process"}

    # Effective world-file set for the baseline advance (variant B): the
    # whole /bin tool surface present in the trial dump, so the new
    # baseline snapshots every `bin-help/*.help.txt` (incl. brand-new
    # tools the PA just grounded). baseline=None — discover from the dump
    # ONLY: write_new_baseline requires bytes for every world file, so a
    # tool that vanished upstream must NOT be carried into the new
    # baseline (it correctly drops out here).
    world_files = world_baseline.effective_world_files(
        config.project_root, fp, baseline=None
    )
    world_sigs = world_baseline.world_dep_signatures(world_files)

    validated = pa_decision.validate_world_refresh_decision(
        project_root=config.project_root,
        pa_dir=pa_dir,
        registry_unit_ids=registry_ids,
        bp_unit_ids=bp_unit_ids,
        fp=fp,
        world_sigs=world_sigs,
        expected_baseline_version=str(trigger.get("baseline_version") or ""),
        expected_mode=expected_mode,
    )
    _log_stripped_world_deps(job.job_id, validated.stripped_world_deps)

    if not validated.accepted:
        pa_decision.write_world_refresh_rejected(
            pa_dir=pa_dir, validated=validated
        )
        return _finalise(PaJobResult(
            job_id=job.job_id,
            kind=job.kind,
            priority=priority_label,
            terminal_status="rejected",
            duration_ms=spawn.duration_ms,
            pa_dir=str(pa_dir),
            exit_code=spawn.exit_code,
            error=(
                f"{len(validated.errors)} validation error(s); see "
                "pa-output/rejected.json"
            ),
        ))

    if not config.pa_apply:
        _write_dry_run_summary(
            pa_dir=pa_dir,
            mode=expected_mode,
            validated=validated,
            project_root=config.project_root,
        )
        print(
            f"{job.job_id} [PA] PA_APPLY=0 — dry-run; "
            f"refresh={len(validated.changes_refresh)} "
            f"new={len(validated.changes_new)} validated but not applied"
        )
        return _finalise(PaJobResult(
            job_id=job.job_id,
            kind=job.kind,
            priority=priority_label,
            terminal_status="dry_run_completed",
            duration_ms=spawn.duration_ms,
            pa_dir=str(pa_dir),
            exit_code=spawn.exit_code,
        ))

    refreshed, created_units, new_baseline = await pa_decision.apply_world_refresh_decision(
        project_root=config.project_root,
        validated=validated,
        fp=fp,
        trigger=trigger,
        pa_queue=queue,
        world_files=world_files,
        label=job.job_id,
        task_dir=task_dir_for_fp,
    )

    refreshed_payload = [{"unit_id": w.unit_id, "version": w.version} for w in refreshed]
    created_payload = [{"unit_id": w.unit_id, "version": w.version} for w in created_units]

    return _finalise(PaJobResult(
        job_id=job.job_id,
        kind=job.kind,
        priority=priority_label,
        terminal_status="completed",
        duration_ms=spawn.duration_ms,
        pa_dir=str(pa_dir),
        exit_code=spawn.exit_code,
        created_versions=refreshed_payload,
        created_units=created_payload,
        new_baseline=new_baseline,
    ))


# ── Conflict-mode context materialisation ──────────────────────────────


def _materialise_conflict_context(
    *,
    project_root: Path,
    pa_dir: Path,
    conflicts: list[pa_decision.StaleBaseConflict],
    retry_num: int,
) -> None:
    """Stage workdir for a conflict-mode rebase spawn.

    - Move `pa-output/` to `pa-output-draft-NN/` so PA's first-pass
      survives as a reference.
    - Archive `pa-result.json` / `.logs/pa-{transcript,stderr,dump}`
      from the first spawn (the next `spawn_pa_cli` would overwrite
      them otherwise).
    - Copy `conflict.md` prompt into the workdir root.
    - Write `conflict-context.json` describing each conflict.
    - Ensure `version-history/units/<uid>/<new_latest>/` is present and
      fresh for every conflicted unit (other PAs published it after
      we first materialised the workdir).
    """
    # 1. Preserve the first-pass draft.
    draft_dir = pa_dir / f"pa-output-draft-{retry_num:02d}"
    src_pa_output = pa_dir / "pa-output"
    if src_pa_output.exists():
        if draft_dir.exists():
            shutil.rmtree(draft_dir)
        shutil.move(str(src_pa_output), str(draft_dir))
    (pa_dir / "pa-output").mkdir(parents=True, exist_ok=True)

    # 2. Archive previous spawn artefacts so the next spawn doesn't
    #    overwrite them. We mirror pa_runner._archive_pa_attempt's
    #    convention but use a "pre-conflict" suffix so transcripts from
    #    earlier internal-error retries stay distinct.
    logs = pa_dir / ".logs"
    logs.mkdir(parents=True, exist_ok=True)
    moves = [
        (pa_dir / "pa-result.json", logs / f"pa-result-pre-conflict-{retry_num:02d}.json"),
        (logs / "pa-transcript.jsonl", logs / f"pa-transcript-pre-conflict-{retry_num:02d}.jsonl"),
        (logs / "pa-stderr.log", logs / f"pa-stderr-pre-conflict-{retry_num:02d}.log"),
        (logs / "dump", logs / f"dump-pre-conflict-{retry_num:02d}"),
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

    # 3. Copy the conflict.md prompt fragment into the workdir.
    conflict_md_src = (
        store.pa_prompts_dir(project_root) / "conflict.md"
    )
    if conflict_md_src.is_file():
        shutil.copyfile(conflict_md_src, pa_dir / "conflict.md")

    # 4. Refresh version-history for each conflicted unit (other PAs
    #    may have published versions after the initial materialise).
    hist_root = pa_dir / "version-history"
    for c in conflicts:
        for ref in store.list_versions(project_root, c.unit_id):
            ver_dest = hist_root / "units" / c.unit_id / ref.version
            ver_dest.mkdir(parents=True, exist_ok=True)
            for name in ("content.md", "manifest.json", "changes.md", "diff.patch"):
                src = ref.version_dir / name
                if src.is_file():
                    shutil.copyfile(src, ver_dest / name)

    # 5. Write conflict-context.json so PA has a structured pointer to
    #    every conflict (avoiding it re-discovering the situation by
    #    reading workdir diffs from scratch).
    ctx = {
        "retry": retry_num,
        "conflicts": [
            {
                "unit_id": c.unit_id,
                "your_base_version": c.original_base,
                "new_latest": c.current_latest,
                "draft_path": (
                    f"pa-output-draft-{retry_num:02d}/units/{c.unit_id}/content.md"
                ),
                "new_latest_path": (
                    f"version-history/units/{c.unit_id}/{c.current_latest}/"
                ),
            }
            for c in conflicts
        ],
    }
    (pa_dir / "conflict-context.json").write_text(
        json.dumps(ctx, indent=2) + "\n", encoding="utf-8"
    )


# ── report_PA.md writer ─────────────────────────────────────────────────


def write_pa_report(
    *,
    pa_dir: Path,
    result: PaJobResult,
    expected_mode: str,
    trigger: dict[str, Any],
) -> Path:
    """Render a human-readable `report_PA.md` next to the PA artefacts.

    One PA job → one file. Aggregates inputs (selected base versions /
    drift summary), the decision (rationales per change), the outcome
    (cost/turns/duration/error), and links to the created versions'
    `changes.md`/`diff.patch`. Conflict-resolution section is currently
    a placeholder ("base was stale at apply: no"); Phase 3 fills it.
    """
    lines: list[str] = []
    kind = result.kind
    priority = result.priority
    status = result.terminal_status

    lines.append(f"# Process Architect report — {kind}")
    lines.append("")
    lines.append(f"- job_id: `{result.job_id}`")
    lines.append(f"- mode: `{expected_mode}` (queue priority: `{priority}`)")
    lines.append(f"- terminal_status: **`{status}`**")
    if result.exit_code is not None:
        lines.append(f"- exit_code: `{result.exit_code}`")
    duration_sec = (result.duration_ms or 0) // 1000
    lines.append(f"- duration: {duration_sec}s")
    if result.error:
        lines.append(f"- error: `{result.error}`")
    lines.append("")

    # Inputs ── trigger context (task/trial/baseline) + base versions ──
    lines.append("## Inputs")
    lines.append("")
    task_id = trigger.get("task_id")
    trial_id = trigger.get("trial_id")
    if task_id:
        lines.append(f"- trigger task: `{task_id}`")
    if trial_id:
        lines.append(f"- trigger trial: `{trial_id}`")
    if expected_mode == "failure_fix":
        score = trigger.get("score")
        score_str = (
            f"{float(score) * 100:.1f}%" if isinstance(score, (int, float)) else "?"
        )
        lines.append(f"- score at trigger: {score_str}")
        outcome = trigger.get("answer_outcome")
        if outcome:
            lines.append(f"- answer_outcome: `{outcome}`")
        failed_dir = trigger.get("failed_task_dir")
        if failed_dir:
            failed_name = Path(str(failed_dir)).name
            lines.append(f"- failed task dir: `{failed_name}`")
    if expected_mode == "refresh":
        unit_id = trigger.get("unit_id")
        base_version = trigger.get("base_version")
        if unit_id:
            lines.append(f"- stale unit: `{unit_id}`")
        if base_version:
            lines.append(f"- base_version: `{base_version}`")
    if expected_mode == "world_refresh":
        baseline_version = trigger.get("baseline_version")
        if baseline_version:
            lines.append(f"- baseline_version: `{baseline_version}`")

    # Selected base versions per unit — read from selected-instructions/
    # (failure_fix) or selected-latest/ (refresh).
    selected_base = _read_selected_base_versions(pa_dir, expected_mode)
    if selected_base:
        lines.append("- selected base versions:")
        for uid, ver in sorted(selected_base.items()):
            lines.append(f"  - `{uid}` → `{ver}`")
    lines.append("")

    # Decision ── per-change rationale + dependencies declared ──
    decision = _read_pa_decision(pa_dir)
    if decision is not None:
        changes_list = (
            decision.get("changes")
            or decision.get("changes_refresh")
            or []
        )
        new_units = decision.get("changes_new") or []
        unchanged = decision.get("unchanged") or []
        lines.append("## Decision")
        lines.append("")
        lines.append(f"- mode (from decision): `{decision.get('mode', '?')}`")
        if changes_list:
            lines.append("")
            lines.append(f"### Changes ({len(changes_list)})")
            for ch in changes_list:
                if not isinstance(ch, dict):
                    continue
                uid = ch.get("unit_id", "?")
                base = ch.get("base_version", "?")
                no_sem = ch.get("no_semantic_change", False)
                rationale = (ch.get("rationale") or "").strip()
                cr = ch.get("conflict_resolution")
                tag_bits: list[str] = []
                if no_sem:
                    tag_bits.append("_no_semantic_change_")
                if isinstance(cr, dict):
                    tag_bits.append(
                        f"_conflict-rebased: `{cr.get('original_base')}` → "
                        f"`{cr.get('rebased_onto')}` ({cr.get('outcome')})_"
                    )
                tag = (" — " + ", ".join(tag_bits)) if tag_bits else ""
                lines.append("")
                lines.append(f"**`{uid}`** (base `{base}`){tag}")
                lines.append("")
                lines.append(f"_Rationale_: {rationale or '(none)'}")
                deps = ch.get("dependencies") or []
                if deps:
                    dep_strs = [
                        f"`{d.get('kind')}:{d.get('path')}`"
                        for d in deps
                        if isinstance(d, dict)
                    ]
                    lines.append("")
                    lines.append(f"_Deps_: {', '.join(dep_strs)}")
        if new_units:
            lines.append("")
            lines.append(f"### New units ({len(new_units)})")
            for nu in new_units:
                if not isinstance(nu, dict):
                    continue
                uid = nu.get("unit_id", "?")
                rationale = (nu.get("rationale") or "").strip()
                lines.append("")
                lines.append(f"**`{uid}`**")
                lines.append("")
                lines.append(f"_Rationale_: {rationale or '(none)'}")
        if unchanged:
            lines.append(f"- unchanged ({len(unchanged)}):")
            for un in unchanged:
                if not isinstance(un, dict):
                    continue
                uid = un.get("unit_id", "?")
                lines.append(f"  - `{uid}`")
        # Subsumed (conflict-retry only): PA decided no new version
        # needed for these conflicted units, with rationale.
        subsumed_list = decision.get("subsumed") or []
        if subsumed_list:
            lines.append("")
            lines.append("### Subsumed (no new version)")
            lines.append("")
            for su in subsumed_list:
                if not isinstance(su, dict):
                    continue
                uid = su.get("unit_id", "?")
                orig = su.get("your_original_base", "?")
                cur = su.get("current_latest", "?")
                rationale = (su.get("rationale") or "").strip()
                lines.append(
                    f"- `{uid}` (your base `{orig}` → their latest `{cur}`):"
                )
                # Full rationale (not truncated) — this is the audit trail
                # for why no version was created.
                lines.append(f"  {rationale}")
        notes = decision.get("notes_for_human")
        if isinstance(notes, str) and notes.strip():
            lines.append("")
            lines.append("### Notes for human")
            lines.append("")
            lines.append(notes.strip())
        lines.append("")
    else:
        # Maybe rejected — surface validation errors.
        rejected = _read_rejected(pa_dir)
        if rejected is not None:
            lines.append("## Decision rejected")
            lines.append("")
            for err in (rejected.get("errors") or [])[:20]:
                lines.append(f"- `{err}`")
            lines.append("")

    # Outcome ── pa-result.json counters ──
    pa_result = _read_pa_result(pa_dir)
    if pa_result:
        lines.append("## Outcome")
        lines.append("")
        for label, key in (
            ("num_turns", "num_turns"),
            ("total_cost_usd", "total_cost_usd"),
            ("duration_ms", "duration_ms"),
            ("model", "model"),
        ):
            val = pa_result.get(key)
            if val is not None:
                lines.append(f"- {label}: `{val}`")
        agg = pa_result.get("pa_aggregate")
        if isinstance(agg, dict):
            for k, v in agg.items():
                lines.append(f"  - {k}: `{v}`")
        lines.append("")

    # Created versions ── links to changes.md / diff.patch ──
    created_all: list[dict[str, str]] = []
    created_all.extend(result.created_versions or [])
    created_all.extend(result.created_units or [])
    if created_all:
        lines.append("## Created versions")
        lines.append("")
        # Links are relative from pa_dir → ../../agent/instructions/... is
        # awkward; use the conventional project-relative form instead.
        for c in created_all:
            uid = c.get("unit_id", "?")
            ver = c.get("version", "?")
            lines.append(
                f"- `{uid}` → `{ver}`  "
                f"(see `agent/instructions/units/{uid}/{ver}/changes.md`, "
                f"`agent/instructions/units/{uid}/{ver}/diff.patch`)"
            )
        if result.new_baseline:
            lines.append(f"- new world baseline: `{result.new_baseline}`")
        lines.append("")

    # Conflict resolution — read from conflict-history.json if present.
    conflict_hist_path = pa_dir / "conflict-history.json"
    lines.append("## Conflict resolution")
    lines.append("")
    if conflict_hist_path.is_file():
        try:
            hist_data = json.loads(conflict_hist_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            hist_data = None
        retries_blocks = (hist_data or {}).get("retries") or []
        lines.append(f"- conflict retries: {len(retries_blocks)}")
        for block in retries_blocks:
            retry_n = block.get("retry", "?")
            confs = block.get("conflicts") or []
            lines.append(f"  - retry {retry_n}:")
            for c in confs:
                lines.append(
                    f"    - `{c.get('unit_id')}`: "
                    f"original_base=`{c.get('original_base')}` → "
                    f"current_latest=`{c.get('current_latest')}`"
                )
        # Per-change conflict_resolution outcomes (PA's stated reconciliation).
        if decision is not None:
            for ch in decision.get("changes") or []:
                if not isinstance(ch, dict):
                    continue
                cr = ch.get("conflict_resolution")
                if isinstance(cr, dict):
                    lines.append(
                        f"  - resolution `{ch.get('unit_id')}`: "
                        f"outcome=`{cr.get('outcome')}` "
                        f"(rebased onto `{cr.get('rebased_onto')}`)"
                    )
    else:
        lines.append("- base was stale at apply: no")
        lines.append("- conflict retries: 0")
    lines.append("")

    report_path = pa_dir / "report_PA.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def _read_selected_base_versions(pa_dir: Path, expected_mode: str) -> dict[str, str]:
    out: dict[str, str] = {}
    if expected_mode == "failure_fix":
        sel_root = pa_dir / "selected-instructions" / "units"
    elif expected_mode == "refresh":
        sel_root = pa_dir / "selected-latest"
    else:
        return out
    if not sel_root.is_dir():
        return out
    for child in sel_root.iterdir():
        if not child.is_dir():
            continue
        ver_path = child / "version.txt"
        if ver_path.is_file():
            ver = ver_path.read_text(encoding="utf-8").strip()
            if ver:
                out[child.name] = ver
    return out


def _read_pa_decision(pa_dir: Path) -> dict[str, Any] | None:
    p = pa_dir / "pa-output" / "pa-decision.json"
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _read_rejected(pa_dir: Path) -> dict[str, Any] | None:
    p = pa_dir / "pa-output" / "rejected.json"
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _read_pa_result(pa_dir: Path) -> dict[str, Any]:
    p = pa_dir / "pa-result.json"
    if not p.is_file():
        return {}
    try:
        text = p.read_text(encoding="utf-8").strip()
        obj = json.loads(text.splitlines()[-1]) if text else {}
    except (OSError, json.JSONDecodeError, IndexError):
        return {}
    return obj if isinstance(obj, dict) else {}

