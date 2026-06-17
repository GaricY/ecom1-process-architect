"""Human-only CLI for instruction-store maintenance.

Three operations:

```
uv run python -m orchestrator.bp_admin retire <unit_id> <vNNNN> [--reason ...]
uv run python -m orchestrator.bp_admin rollback <unit_id> --from <vNNNN>
    [--task-dir <existing trial dir>] [--empty-deps] [--reason ...]
uv run python -m orchestrator.bp_admin strip-world-deps [--dry-run]
    [--keep-snapshots]
```

`retire` flips `manifest.status` to `retired`. The artifact stays on
disk; the resolver simply stops selecting it.

`rollback` creates a new version whose `content.md` matches the
`--from` version, then:

- with `--task-dir <path>`, re-hashes the parent's declared
  dependencies against that trial's `vault/`/`bin-help/`/static
  files so the new version becomes "matching" for runs against the
  same world.
- without `--task-dir` (or with `--empty-deps`), persists an empty
  dependency list, which means the new version always matches and
  becomes the latest active winner. Pick this when the source files
  have moved and you just want the prior text back in play.

`strip-world-deps` is the **only** command that mutates an existing
`vNNNN/` artifact in place. It walks every committed version manifest
and removes any dependency entry whose `(kind, path)` is listed in
`instructions/world.json`. Snapshot bytes for those deps are also
unlinked unless `--keep-snapshots`. This violates the immutability
rule documented in `agent/CLAUDE.md` — it is a deliberate one-shot
migration whenever the world list is extended, never a recurring PA
flow. The decision validator rejects world-deps from any new manifest,
so the strip is permanent until the world list grows.

None of these commands spawn the Process Architect.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .instructions import store, versioning
from .instructions.fingerprints import FingerprintIndex, normalize


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def cmd_retire(args: argparse.Namespace) -> int:
    project_root = _project_root()
    ref = store.get_version(project_root, args.unit_id, args.version)
    if ref is None:
        print(f"error: {args.unit_id}/{args.version} not found", file=sys.stderr)
        return 1
    reason = args.reason or "manual retire via bp_admin"
    versioning.retire_version(
        project_root=project_root,
        unit_id=args.unit_id,
        version=args.version,
        reason=reason,
    )
    print(f"retired {args.unit_id}/{args.version} ({reason})")
    return 0


def cmd_rollback(args: argparse.Namespace) -> int:
    project_root = _project_root()
    src = store.get_version(project_root, args.unit_id, args.from_version)
    if src is None:
        print(
            f"error: {args.unit_id}/{args.from_version} not found",
            file=sys.stderr,
        )
        return 1
    src_manifest = store.load_manifest(src)
    content = src.content_path.read_text(encoding="utf-8")

    use_empty_deps = args.empty_deps or not args.task_dir
    if args.task_dir:
        task_dir = Path(args.task_dir).resolve()
        if not (task_dir / "vault").is_dir():
            print(
                f"warn: {task_dir}/vault not found — workspace deps will hash "
                "as missing"
            )
    else:
        task_dir = project_root / ".bp_admin_empty_taskdir"
        task_dir.mkdir(parents=True, exist_ok=True)
    fp = FingerprintIndex(task_dir=task_dir, project_root=project_root)

    if use_empty_deps:
        deps_payload: list[dict[str, object]] = []
        deps_label = "empty (always-match rollback)"
    else:
        deps_payload = [
            {
                "kind": d.kind,
                "path": d.path,
                "why": d.why,
                **({"required": False} if not d.required else {}),
            }
            for d in src_manifest.dependencies
        ]
        deps_label = f"reused from {args.from_version} ({len(deps_payload)} deps)"

    rationale = (
        args.reason
        or f"Manual rollback: restoring {args.from_version} content under "
        f"{deps_label}."
    )
    new_input = versioning.NewVersionInput(
        unit_id=args.unit_id,
        base_version=args.from_version,
        content=content,
        no_semantic_change=False,
        mode="rollback",
        created_by="bp_admin",
        trigger={"command": "rollback", "from_version": args.from_version},
        rationale=rationale,
        dependencies=deps_payload,
        rollback_note=(
            f"Rolled back to {args.from_version} text; retire this version "
            "if it regresses or recreate via another rollback."
        ),
    )
    written = versioning.write_new_version(
        project_root=project_root, new=new_input, fp=fp
    )
    print(
        f"created {written.unit_id}/{written.version} (deps={deps_label}, "
        f"dependency_count={written.dependency_count})"
    )
    return 0


def _snapshot_rel(kind: str, path: str) -> str:
    """Mirror of versioning._snapshot_rel — kept private so bp_admin can prune.

    Matches the on-disk layout that `versioning.write_new_version` builds
    under `vNNNN/dependency_snapshot/`.
    """
    if kind == "workspace":
        return "workspace/" + path.lstrip("/")
    if kind == "bin_help":
        return "bin-help/" + path
    if kind == "static":
        return "static/" + path
    if kind == "sql_table":
        return "sql-table/" + path.strip().lower() + ".schema.txt"
    raise ValueError(f"unknown dependency kind {kind!r}")


def _prune_empty_dirs_up_to(start: Path, stop: Path) -> None:
    """Remove `start` and its empty parents, stopping before `stop`."""
    try:
        start_resolved = start.resolve()
        stop_resolved = stop.resolve()
    except OSError:
        return
    cur = start_resolved
    while cur != stop_resolved and stop_resolved in cur.parents:
        if not cur.is_dir():
            return
        try:
            next(cur.iterdir())
            return  # not empty
        except StopIteration:
            pass
        except OSError:
            return
        try:
            cur.rmdir()
        except OSError:
            return
        cur = cur.parent


def cmd_strip_world_deps(args: argparse.Namespace) -> int:
    """One-shot migration: remove world-file deps from every manifest."""
    project_root = _project_root()
    from .instructions import world_baseline
    world_files = world_baseline.load_world_files(project_root)
    world_sigs = world_baseline.world_dep_signatures(world_files)

    dry_run = bool(args.dry_run)
    keep_snapshots = bool(args.keep_snapshots)

    units_root = store.units_dir(project_root)
    if not units_root.is_dir():
        print(f"error: {units_root} does not exist", file=sys.stderr)
        return 1

    total_versions = 0
    total_touched = 0
    total_deps_removed = 0
    snapshots_unlinked = 0

    for unit_dir in sorted(units_root.iterdir()):
        if not unit_dir.is_dir():
            continue
        unit_id = unit_dir.name
        for ref in store.list_versions(project_root, unit_id):
            total_versions += 1
            manifest_path = ref.manifest_path
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                print(
                    f"skip {unit_id}/{ref.version}: cannot read manifest ({exc})",
                    file=sys.stderr,
                )
                continue
            deps = data.get("dependencies")
            if not isinstance(deps, list):
                continue
            kept: list[Any] = []
            removed: list[dict[str, Any]] = []
            for d in deps:
                if not isinstance(d, dict):
                    kept.append(d)
                    continue
                kind = d.get("kind")
                path = d.get("path")
                if not isinstance(kind, str) or not isinstance(path, str):
                    kept.append(d)
                    continue
                if (kind, normalize(kind, path)) in world_sigs:
                    removed.append(d)
                else:
                    kept.append(d)
            if not removed:
                continue
            total_touched += 1
            total_deps_removed += len(removed)
            paths_str = ", ".join(str(d.get("path", "?")) for d in removed)
            prefix = "[dry-run] " if dry_run else ""
            print(
                f"{prefix}{unit_id}/{ref.version}: -{len(removed)} world dep(s) "
                f"({paths_str})"
            )
            if dry_run:
                continue
            data["dependencies"] = kept
            manifest_path.write_text(
                json.dumps(data, indent=2) + "\n", encoding="utf-8"
            )
            if keep_snapshots:
                continue
            for d in removed:
                kind_s = str(d["kind"])
                path_s = str(d["path"])
                snap_file = ref.snapshot_dir / _snapshot_rel(kind_s, path_s)
                if snap_file.is_file():
                    try:
                        snap_file.unlink()
                        snapshots_unlinked += 1
                        _prune_empty_dirs_up_to(snap_file.parent, ref.snapshot_dir)
                    except OSError as exc:
                        print(
                            f"  warn: could not unlink snapshot {snap_file}: {exc}",
                            file=sys.stderr,
                        )

    print()
    suffix = " (dry-run — no changes written)" if dry_run else ""
    print(
        f"summary: scanned {total_versions} versions across "
        f"{sum(1 for _ in units_root.iterdir() if _.is_dir())} units; "
        f"touched {total_touched} manifests; "
        f"removed {total_deps_removed} world dep(s); "
        f"unlinked {snapshots_unlinked} snapshot file(s){suffix}"
    )
    return 0


def cmd_world_baseline_init(args: argparse.Namespace) -> int:
    project_root = _project_root()
    from .instructions import world_baseline
    task_dir = Path(args.from_task_dir).resolve()
    if not task_dir.is_dir():
        print(f"error: --from-task-dir not a directory: {task_dir}", file=sys.stderr)
        return 1
    if not (task_dir / "vault").is_dir():
        print(
            f"error: {task_dir}/vault not found — expected an existing trial dump",
            file=sys.stderr,
        )
        return 1
    rationale = args.reason or (
        f"Manual seed from trial dump at {task_dir}. Pre-drift baseline so "
        "world_refresh PA can diff against upstream evolution."
    )
    try:
        ref = world_baseline.init_baseline_from_task_dir(
            project_root=project_root,
            task_dir=task_dir,
            rationale=rationale,
        )
    except (FileExistsError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"created world_baseline/{ref.version} from {task_dir}")
    print(f"  manifest:  {ref.manifest_path}")
    print(f"  snapshot:  {ref.snapshot_dir}")
    print(f"  diff:      {ref.diff_path} (empty for v0001)")
    print(f"  changes:   {ref.changes_path}")
    return 0


def cmd_world_baseline_list(args: argparse.Namespace) -> int:
    project_root = _project_root()
    from .instructions import world_baseline
    refs = world_baseline.list_baselines(project_root)
    if not refs:
        print("(no baselines committed yet — seed via `world-baseline init`)")
        return 0
    for ref in refs:
        manifest = world_baseline.load_baseline_manifest(ref)
        print(
            f"{ref.version}  parent={manifest.parent or 'none'}  "
            f"files={len(manifest.files)}  "
            f"created_at={manifest.created_at}  "
            f"created_by={manifest.created_by}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bp_admin",
        description=(
            "Human-only maintenance for agent/instructions/units/. Use "
            "retire to take a bad version out of rotation, rollback to "
            "re-deploy an older version's text under fresh dependency "
            "hashes."
        ),
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("retire", help="mark a version retired")
    pr.add_argument("unit_id")
    pr.add_argument("version", help="e.g. v0007")
    pr.add_argument("--reason", default=None)
    pr.set_defaults(func=cmd_retire)

    pb = sub.add_parser(
        "rollback",
        help="create a new version from an older version's text",
    )
    pb.add_argument("unit_id")
    pb.add_argument(
        "--from",
        dest="from_version",
        required=True,
        help="parent version, e.g. v0006",
    )
    pb.add_argument(
        "--task-dir",
        default=None,
        help=(
            "path to an existing trial task_dir (vault/, bin-help/) used "
            "to hash the parent's declared dependencies. Without this, "
            "the rollback version is written with empty deps and always "
            "matches."
        ),
    )
    pb.add_argument(
        "--empty-deps",
        action="store_true",
        help="force empty dependency list even when --task-dir is given",
    )
    pb.add_argument("--reason", default=None)
    pb.set_defaults(func=cmd_rollback)

    ps = sub.add_parser(
        "strip-world-deps",
        help=(
            "remove world-file deps from every manifest in place. "
            "Deliberate immutability exception — run only when "
            "`instructions/world.json` is extended."
        ),
    )
    ps.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would change without writing.",
    )
    ps.add_argument(
        "--keep-snapshots",
        action="store_true",
        help=(
            "leave `dependency_snapshot/<world-rel>` files on disk. "
            "Default is to unlink them too, since the manifest no longer "
            "references those bytes."
        ),
    )
    ps.set_defaults(func=cmd_strip_world_deps)

    pwb = sub.add_parser(
        "world-baseline",
        help="manage `instructions/world_baseline/vNNNN/` snapshots.",
    )
    wb_sub = pwb.add_subparsers(dest="world_baseline_cmd", required=True)

    wb_init = wb_sub.add_parser(
        "init",
        help=(
            "seed `v0001` from an existing trial dump (vault/ + bin-help/). "
            "Pick a trial that predates the upstream drift you want to "
            "experiment against — otherwise baseline == live and "
            "world_refresh will never fire."
        ),
    )
    wb_init.add_argument(
        "--from-task-dir",
        dest="from_task_dir",
        required=True,
        help="absolute path to the source trial task_dir.",
    )
    wb_init.add_argument(
        "--reason",
        default=None,
        help="rationale stored in changes.md / manifest.rationale.",
    )
    wb_init.set_defaults(func=cmd_world_baseline_init)

    wb_list = wb_sub.add_parser(
        "list",
        help="list committed baselines (ascending).",
    )
    wb_list.set_defaults(func=cmd_world_baseline_list)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
