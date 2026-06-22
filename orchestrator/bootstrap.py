"""Pre-bootstrap dump + bin-help builder for each per-trial task directory.

`PreBootstrapDumper` always-fresh-copies live workspace state into the task
directory:

- `tree.md`        — `tree -L 2` rendering of the live workspace.
- `vault/docs/`    — full copy of `/docs`.
- `vault/bin/`     — full copy of `/bin`.
- `vault/<...>/AGENTS.md`, `vault/<...>/README.md` — every active policy
  marker, at its relative workspace path with case preserved.
- `.logs/pre-bootstrap-manifest.json` — manifest with timestamp, contract
  version, benchmark id, and (relative_path, sha256) for every copied file.

The static instruction folder (`agent/static-instructions/`) is copied
verbatim into the task directory root so `CLAUDE.md`, `.claude/`,
`business_processes/`, `runtime_prelude.py`, `workspace.py` are always
available exactly as shipped.

`BinHelpBootstrapper` then walks `vault/bin/` for files without extension,
runs `/bin/<tool> --help` live, and writes `bin-help/<relative_path>.help.txt`.
In the same pass it queries the warehouse `sqlite_schema` via `/bin/sql` and
writes a formatted per-table view to `bin-help/sqlite_schema.txt` (see
`orchestrator.sql_schema`). A content hash of the resulting files is recorded
in `.logs/bin-help-manifest.json` for local inspection.
"""

from __future__ import annotations

import concurrent.futures
import csv
import hashlib
import json
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from bitgn.vm.ecom.ecom_connect import EcomRuntimeClientSync
from bitgn.vm.ecom.ecom_pb2 import (
    NODE_KIND_FILE,
    ExecRequest,
    FindRequest,
    ListRequest,
    ReadRequest,
    TreeRequest,
)
from connectrpc.code import Code
from connectrpc.errors import ConnectError
from google.protobuf.json_format import MessageToDict

from .proc_schema import build_recovered_schema_doc
from .sql_schema import format_from_csv, parse_csv_rows

READ_WORKERS = 10
EXEC_WORKERS = 10

# Retry layer for every harness RPC — applied at our wrapper, not the SDK.
# Goal: the agent should never trip on a transient harness blip.
VM_RETRY_ATTEMPTS = 5
VM_RETRY_BACKOFF_SEC = 0.2  # initial; multiplied by attempt index


class RetryingVM:
    """Proxy that retries every callable method on exception (5 attempts).

    Exception, `read` ONLY: a `NOT_FOUND` (404) is never retried — for a
    file read it's deterministic (the path doesn't exist and won't appear
    mid-trial), so retrying only burns ~2s of backoff. This short-circuit is
    scoped to `read` on purpose: on `exec`/`tree` a `NOT_FOUND` may be
    transient or carry different semantics, and skipping retries on an
    action RPC like `exec` is unsafe. Transient failures (timeouts /
    `UNAVAILABLE` / connection blips) always get the full retry budget.
    """

    _MAX_ATTEMPTS = VM_RETRY_ATTEMPTS
    _BACKOFF_SEC = VM_RETRY_BACKOFF_SEC

    def __init__(self, inner) -> None:
        self._inner = inner

    def __getattr__(self, name: str):
        attr = getattr(self._inner, name)
        if not callable(attr):
            return attr

        # 404 fail-fast is read-only — never short-circuit exec/tree/etc.
        fail_fast_404 = name == "read"

        def wrapped(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(self._MAX_ATTEMPTS):
                try:
                    return attr(*args, **kwargs)
                except ConnectError as exc:
                    if fail_fast_404 and exc.code == Code.NOT_FOUND:
                        raise  # missing file — retrying can't help
                    last_exc = exc
                    if attempt < self._MAX_ATTEMPTS - 1:
                        time.sleep(self._BACKOFF_SEC * (attempt + 1))
                except Exception as exc:
                    last_exc = exc
                    if attempt < self._MAX_ATTEMPTS - 1:
                        time.sleep(self._BACKOFF_SEC * (attempt + 1))
            assert last_exc is not None
            raise last_exc

        return wrapped


def make_vm(harness_url: str) -> RetryingVM:
    """Construct the canonical VM client wrapped with retries."""
    return RetryingVM(EcomRuntimeClientSync(harness_url))

PRE_BOOTSTRAP_VERSION = "5"
# v2: pre-bootstrap-manifest.json gains `rule_source` per file and the dump
# now follows non-JSON markdown refs transitively (rule 3) plus drops one
# `/proc/<family>/__sample__.json` per /proc family (rule 4). Rule indices
# match `ecom-tasks/dump_t43_selective.py`.
# v3: rule 1 (README.md / AGENTS.md any case) now matches at any depth
# visible in the staged trees — the depth-2 root tree catches
# `/proc/README.md` and a /proc tree (already fetched for rule 4) catches
# `/proc/<family>/README.md`. Previously rule 1 only fired for root-level
# index files plus whatever /docs/, /run/, /bin/ swept up.
# v4: rule-4 `__sample__.json` files moved OUT of the executor's `vault/`
# into `.logs/world-samples/proc/<family>/` (see `WORLD_SAMPLES_SUBDIR`).
# They were only ever record-shape evidence for the PA world_refresh/
# world_create modes; the executor queries live proc state via `/bin/sql`.
# `pa_workdir` grafts them back into the world-mode PA workdir's vault.
# v5: the `/proc` tree walk (stage 2b) + rule-4 proc samples (stage 7) are
# gated behind `world_modes_enabled` (WORLD_CREATE_ENABLED or
# WORLD_REFRESH_ENABLED). They feed ONLY the world_refresh/world_create PA
# workdirs; on a normal trial both are dead weight, and the level-2 `/proc`
# walk fans out to every record in every family (the "10k+ entries" the
# strategy below was meant to avoid) — the dominant bootstrap cost. With
# world modes off, `proc_node` stays empty so stages 3b-proc and 7 no-op;
# `/proc/README.md` still survives via the depth-2 root tree (rule 1).

# Doc extensions rescanned by rule 3 (transitive).
_DOC_EXTS = {".md", ".txt"}

# Cap on how many transitive refs we'll pull in — keeps a misbehaving
# regex / cycle from running away. ~5-15 expected per trial.
_RULE3_MAX_FETCHES = 50

# Fallback top-level dirs — used ONLY if the live root tree couldn't be
# read, so ref extraction still works. Normally the real set is derived
# per-trial from the dump via `_top_level_dirs` (covers `/uploads` and any
# dir the organizer adds/renames without a code change).
_FALLBACK_ROOT_DIRS = ("docs", "bin", "proc", "run")


def _top_level_dirs(root_tree_node: dict) -> tuple[str, ...]:
    """Top-level workspace directory names from the level-2 root tree.

    Drives ref extraction: the bare-path regex branch, root-relative link
    resolution, and the rule-3 directory-mention skip. Read live rather
    than hardcoded so the extractor stays correct as the workspace tree
    changes (the organizer is known to relocate/add dirs).
    """
    dirs = tuple(
        name
        for c in (root_tree_node.get("children") or [])
        if c.get("kind") == "NODE_KIND_DIR"
        and (name := (c.get("name") or "").strip("/"))
    )
    return dirs or _FALLBACK_ROOT_DIRS


def _build_link_re(root_dirs: tuple[str, ...]) -> "re.Pattern[str]":
    """Markdown `](path)` link OR backtick token OR bare `/<root>/...` path.

    The bare-path branch is scoped to the live top-level dirs so a stray
    `/foo/bar` in prose isn't mistaken for a workspace path.
    """
    alt = "|".join(re.escape(d) for d in root_dirs)
    return re.compile(
        r"\]\(([^)]+)\)"
        r"|`([^`]+)`"
        rf"|(?<![\w/])(/(?:{alt})/[A-Za-z0-9._/\-]+)"
    )


def _norm_ref(raw: str, base_dir: str, root_dirs: tuple[str, ...]) -> str | None:
    """Resolve a raw link/backtick token into an absolute vault path, or None."""
    t = raw.strip().split("#", 1)[0].split("?", 1)[0].strip()
    if not t or t.startswith(("http://", "https://", "mailto:")):
        return None
    # A real workspace path has no whitespace. Tokens with spaces/newlines
    # come from backtick command examples (`/bin/payments refund <id>`) and
    # from the backtick regex greedily swallowing whole ```fenced blocks
    # across newlines — malformed paths that only yield dead reads.
    if any(c.isspace() for c in t):
        return None
    # Trailing slash ⇒ a directory mention (`/docs/policy-updates/`,
    # `/proc/customers/`), not a readable file. Don't follow it.
    if t.endswith("/"):
        return None
    if t.startswith("/"):
        path = t
    elif t.split("/", 1)[0] in root_dirs:
        # Root-relative link written without a leading slash, e.g.
        # `docs/security.md` inside /docs/checkout.md. Joining onto base_dir
        # would double the segment → /docs/docs/security.md (a dead path),
        # so a leading top-level dir name is treated as root-relative.
        path = "/" + t
    elif "/" in t or t.endswith((".md", ".txt", ".json")):
        path = os.path.normpath(os.path.join(base_dir, t))
    else:
        return None
    path = "/" + path.lstrip("/")
    return path.rstrip("/") or None


def _extract_refs(
    text: str,
    base_dir: str,
    link_re: "re.Pattern[str]",
    root_dirs: tuple[str, ...],
) -> set[str]:
    refs: set[str] = set()
    for m in link_re.finditer(text):
        raw = m.group(1) or m.group(2) or m.group(3)
        if not raw:
            continue
        r = _norm_ref(raw, base_dir, root_dirs)
        if r:
            refs.add(r)
    return refs


def _classify_rule(ws_path: str) -> str:
    """Categorise `ws_path` into the rule that put it in vault/.

    Used only for `pre-bootstrap-manifest.json` `rule_source` so an
    operator can grep which rule fired. Categories follow the bulk-dump
    stages in `pre_bootstrap_dump`:

    - `rule1:index`    — README.md / AGENTS.MD anywhere (case-insensitive
                         basename match — matches the reference
                         `ecom-tasks/dump_t43_selective.py` rule 1).
                         Wins over rule2:docs / rule2:bin / rule2:run for
                         index files inside those subtrees.
    - `rule2:bin`      — under `/bin/`.
    - `rule2:run`      — under `/run/`.
    - `rule2:docs`     — under `/docs/` (stage-2 bulk dump; rule-3
                         would reach the same files transitively but
                         the dump already pulled them).
    - `rule2:other`    — other paths produced by stage-2 bulk reads
                         (defensive — should be rare in practice).

    Note: paths added by rule-3 transitive scan are tagged
    `rule3:transitive-from <doc>` directly in
    `pre_bootstrap_dump`; `/proc/<fam>/__sample__.json` paths get
    `rule4:proc_sample[<fam>]`. `_classify_rule` never returns those —
    only stage-2 byproducts.
    """
    base = ws_path.rsplit("/", 1)[-1].lower()
    if base in {"readme.md", "agents.md"}:
        return "rule1:index"
    if ws_path.startswith("/bin/"):
        return "rule2:bin"
    if ws_path.startswith("/run/"):
        return "rule2:run"
    if ws_path.startswith("/docs/"):
        return "rule2:docs"
    return "rule2:other"


_INDEX_BASENAMES = {"readme.md", "agents.md"}

# Index-file names looked up under /proc in stage 5b, via the harness Find
# RPC (which returns the REAL on-disk paths — no case-guessing, no dupes).
# Prod casing is inconsistent (observed `README.md` but `AGENTS.MD`), so we
# query a few spellings and union the results; Find may also match case-
# insensitively, in which case the extra spellings just dedupe to the same
# real path. Querying a name Find doesn't match simply returns nothing.
_PROC_INDEX_NAMES = (
    "README.md",
    "README.MD",
    "readme.md",
    "AGENTS.MD",
    "AGENTS.md",
    "agents.md",
)


def _walk_index_files(children: list[dict], base: str, out: list[str]) -> None:
    """Append paths of any README.md / AGENTS.md (case-insensitive) under `children`.

    Recurses through directory nodes. `base` is the absolute prefix of
    `children`'s parent (e.g. ``""`` for the root tree, ``"/proc"`` for
    a /proc-rooted tree). Output paths are absolute (leading slash).
    """
    for child in children:
        cname = child.get("name") or ""
        if not cname:
            continue
        ckind = child.get("kind", "")
        cpath = base.rstrip("/") + "/" + cname.lstrip("/")
        if not cpath.startswith("/"):
            cpath = "/" + cpath
        if ckind == "NODE_KIND_FILE" and cname.lower() in _INDEX_BASENAMES:
            out.append(cpath)
        elif ckind == "NODE_KIND_DIR":
            _walk_index_files(child.get("children") or [], cpath, out)
# v2: adds bin-help/sqlite_schema.txt (live /bin/sql discovery query).
BIN_HELP_VERSION = "2"

SQLITE_SCHEMA_QUERY = (
    "select type, name, sql from sqlite_schema "
    "where sql is not null order by type, name;"
)
SQLITE_SCHEMA_FILE = "sqlite_schema.txt"

# Fallback for when `/bin/sql` is unavailable (the PROD MS SQL cluster outage):
# the warehouse is still served as a file-shaped JSON projection under /proc, so
# we sample records per family and reconstruct the schema doc (see
# `_recover_schema_from_proc` + `orchestrator.proc_schema`). The header note is
# fixed text describing the recovery provenance.
PROC_SCHEMA_RECOVERY_NOTE = (
    "Recovered from live /proc JSON records via /bin/jq and /bin/cat. "
    "/bin/sql is unavailable in this prod runtime"
)
# Records read per /proc family for inference — enough to surface optional
# fields + enum values; FK detection is prefix-based so it survives sampling
# gaps. Sampled evenly across the family's partitions.
PROC_SCHEMA_SAMPLE_PER_FAMILY = 60
# Upper bound on the per-family find() (it also yields the total record count).
PROC_SCHEMA_FIND_LIMIT = 10000

# Subdirectory inside every per-trial task_dir where stream/audit/manifest
# artifacts live. Working docs (scratchpad/state/answer/result) and inputs
# (task.md, CLAUDE.md, vault/, …) stay at task_dir root.
LOGS_DIR_NAME = ".logs"

# Rule-4 proc samples (one `__sample__.json` per /proc family) are record-
# shape evidence for the PA `world_refresh` / `world_create` modes ONLY —
# the executor queries live proc state via `/bin/sql` and does not need
# them. They live under `.logs/` so they never appear in the executor's
# `vault/`; `pa_workdir._materialise_world_refresh_workdir` grafts the
# `proc/` subtree into the PA workdir's `vault/proc/` where the world
# prompts expect them.
WORLD_SAMPLES_SUBDIR = "world-samples"


def world_samples_dir(task_dir: Path) -> Path:
    """Dir holding rule-4 proc samples for PA world_refresh/world_create.

    Under `.logs/` (executor-invisible). Samples live at
    `world_samples_dir(task_dir)/proc/<family>/__sample__.json`.
    """
    return task_dir / LOGS_DIR_NAME / WORLD_SAMPLES_SUBDIR


# ── Pre-bootstrap dump ──────────────────────────────────────────────────


@dataclass
class PreBootstrapResult:
    task_dir: Path
    vault_dir: Path
    tree_path: Path
    manifest_path: Path
    files_copied: int


def _safe_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _safe_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _format_tree_node(node: dict, prefix: str = "", is_last: bool = True) -> list[str]:
    name = node.get("name") or "/"
    kind = node.get("kind", "")
    branch = "└── " if is_last else "├── "
    suffix = "/" if kind == "NODE_KIND_DIR" else ""
    lines = [f"{prefix}{branch}{name}{suffix}"]
    children = list(node.get("children") or [])
    child_prefix = f"{prefix}{'    ' if is_last else '│   '}"
    for idx, child in enumerate(children):
        lines.extend(
            _format_tree_node(child, prefix=child_prefix, is_last=idx == len(children) - 1)
        )
    return lines


def _render_tree_md(tree_dict: dict) -> str:
    root = tree_dict.get("root") or {}
    root_name = root.get("name") or "/"
    body = [f"tree l2 {root_name}", root_name + "/"]
    children = list(root.get("children") or [])
    for idx, child in enumerate(children):
        body.extend(_format_tree_node(child, prefix="", is_last=idx == len(children) - 1))
    return "\n".join(body) + "\n"


def _walk_tree_dirs(node: dict, base: str = "") -> list[str]:
    """Yield every directory path under `node` (absolute, leading slash)."""
    name = node.get("name") or ""
    kind = node.get("kind", "")
    if kind != "NODE_KIND_DIR":
        return []
    here = base.rstrip("/") + "/" + name if name else (base or "/")
    if not here.startswith("/"):
        here = "/" + here.lstrip("/")
    out = [here]
    for child in node.get("children") or []:
        out.extend(_walk_tree_dirs(child, here))
    return out


def _read_one(vm, path: str) -> tuple[bytes, str] | None:
    """Single ws.read. Retries are handled inside the VM wrapper."""
    try:
        res = vm.read(ReadRequest(path=path))
    except Exception:
        return None
    content = res.content or ""
    sha = res.sha256 or hashlib.sha256(content.encode("utf-8")).hexdigest()
    return content.encode("utf-8"), sha


def _collect_file_paths(node: dict, base: str) -> list[str]:
    """Walk `node`'s children, treating `base` as the absolute path of `node`.

    Returns absolute paths of every NODE_KIND_FILE descendant. The root entry's
    own name is ignored — per proto, clients assemble paths from the requested
    root + recursive child names.
    """
    paths: list[str] = []
    for child in node.get("children") or []:
        child_name = child.get("name") or ""
        if not child_name:
            continue
        kind = child.get("kind") or ""
        if base == "/" or base == "":
            child_path = "/" + child_name
        else:
            child_path = base.rstrip("/") + "/" + child_name
        if kind == "NODE_KIND_FILE":
            paths.append(child_path)
        elif kind == "NODE_KIND_DIR":
            paths.extend(_collect_file_paths(child, child_path))
    return paths


def _read_paths_parallel(
    harness_url: str,
    paths: list[str],
    *,
    workers: int,
) -> dict[str, tuple[bytes, str] | None]:
    """Parallel ws.read over `paths`. Returns path → (content, sha) | None."""
    results: dict[str, tuple[bytes, str] | None] = {}
    if not paths:
        return results

    def _worker(path: str) -> tuple[str, tuple[bytes, str] | None]:
        # Per-thread client — the underlying pyqwest SyncClient is fine across
        # threads in practice, but a dedicated client per worker keeps the
        # request pipeline cleanly isolated and avoids assumptions.
        vm = make_vm(harness_url)
        return path, _read_one(vm, path)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for path, result in pool.map(_worker, paths):
            results[path] = result
    return results


def _copy_static_instructions(static_dir: Path, task_dir: Path) -> int:
    """Copy `static-instructions/` verbatim into task_dir root.

    `.claude/`, `runtime_prelude.py`, `workspace.py` (and any future
    siblings) land at the task directory root. The versioned executor
    prompt (`CLAUDE.md`) and `business_processes/*.md` are rendered by
    the instruction resolver after this dump completes, so they are NOT
    sourced from `static-instructions/` anymore — see
    `orchestrator.instructions.resolve_and_render`.
    """
    if not static_dir.is_dir():
        raise FileNotFoundError(f"static-instructions/ not found at {static_dir}")
    count = 0
    for entry in static_dir.rglob("*"):
        if entry.is_dir():
            continue
        rel = entry.relative_to(static_dir)
        dest = task_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(entry, dest)
        count += 1
    return count


def pre_bootstrap_dump(
    *,
    harness_url: str,
    task_dir: Path,
    static_instructions_dir: Path,
    benchmark_id: str,
    task_id: str,
    trial_id: str,
    world_modes_enabled: bool = False,
) -> PreBootstrapResult:
    """Always-fresh dump of live workspace into the per-trial task directory.

    Strategy: 1× tree(root, level=2) for tree.md + top-level entries, then
    scoped tree(level=0) for /docs, /run, /bin to enumerate files (avoids
    walking /proc which has 10k+ entries). All file reads issued in parallel.

    `world_modes_enabled` (WORLD_CREATE_ENABLED or WORLD_REFRESH_ENABLED)
    gates the only /proc-walking work — stage 2b (the level-2 `/proc` tree)
    and stage 7 (rule-4 per-family JSON samples). Both feed the world PA
    modes exclusively; with them off we skip the `/proc` walk entirely.
    """
    task_dir.mkdir(parents=True, exist_ok=True)
    vault = task_dir / "vault"
    vault.mkdir(parents=True, exist_ok=True)
    # Executor's free-form workspace; `Write(./tmp/**)` permission is granted
    # in static-instructions/.claude/settings.json so snippets-of-thought,
    # intermediate CSV dumps and the post-mortem live here.
    (task_dir / "tmp").mkdir(parents=True, exist_ok=True)

    vm = make_vm(harness_url)
    manifest: list[dict] = []

    # 1. tree level 2 → tree.md + top-level files.
    root_tree_node: dict = {}
    try:
        tree2 = vm.tree(TreeRequest(root="", level=2))
        root_tree_node = MessageToDict(tree2.root, preserving_proto_field_name=True)
        tree_md = _render_tree_md({"root": root_tree_node})
    except Exception as exc:
        tree_md = f"tree l2 /\n(tree fetch failed: {exc})\n"
    tree_path = task_dir / "tree.md"
    _safe_write_text(tree_path, tree_md)

    # 2. Scoped tree(level=0) for /docs, /run, /bin — collect paths.
    scoped_paths: list[str] = []
    for scope in ("/docs", "/run", "/bin"):
        try:
            sub = vm.tree(TreeRequest(root=scope, level=0))
            sub_node = MessageToDict(sub.root, preserving_proto_field_name=True)
            scoped_paths.extend(_collect_file_paths(sub_node, base=scope))
        except Exception:
            continue

    # 2b. /proc tree (level=2) — used both for rule 1 (READMEs at /proc
    #     and /proc/<family>) and rule 4 (sample JSONs). Best-effort:
    #     if /proc is unavailable the trees stay empty and rule 1/4
    #     fall back to whatever was already collected elsewhere.
    #
    #     GATED on `world_modes_enabled`: this is the only place we walk
    #     /proc, and a level-2 walk fans out to every record in every
    #     family (the "10k+ entries" the strategy avoids) — the dominant
    #     bootstrap cost. Its only consumers are the world_refresh/
    #     world_create PA modes (per-family READMEs + rule-4 samples). With
    #     world modes off, `proc_node` stays empty, so stages 3b-proc and 7
    #     no-op and `/proc/README.md` still arrives via the depth-2 root
    #     tree (rule 1, stage 3b below).
    proc_node: dict = {}
    if world_modes_enabled:
        try:
            proc_tree = vm.tree(TreeRequest(root="/proc", level=2))
            proc_node = MessageToDict(
                proc_tree.root, preserving_proto_field_name=True
            )
        except Exception:
            pass

    # 3. Top-level files from the root tree_l2 (e.g. /AGENTS.MD).
    root_top_files: list[str] = []
    for child in root_tree_node.get("children") or []:
        if child.get("kind") == "NODE_KIND_FILE":
            root_top_files.append("/" + (child.get("name") or "").lstrip("/"))

    # 3b. Rule 1 — README.md / AGENTS.md anywhere reachable in the staged
    #     trees. root tree2 reaches depth 2 from / (catches
    #     `/proc/README.md`); proc_node reaches depth 2 from /proc
    #     (catches `/proc/<family>/README.md`). Duplicates fold via the
    #     `set` below — `/AGENTS.MD` arrives from both root_top_files and
    #     here, /docs/README.md and /bin/README.md arrive from
    #     scoped_paths and here.
    index_paths: list[str] = []
    _walk_index_files(root_tree_node.get("children") or [], "", index_paths)
    _walk_index_files(proc_node.get("children") or [], "/proc", index_paths)

    all_paths = sorted(set(scoped_paths + root_top_files + index_paths))

    # 4. Parallel reads.
    fetched = _read_paths_parallel(harness_url, all_paths, workers=READ_WORKERS)

    # 5. Write to vault preserving relative path. /bin/* placeholders stay empty.
    dumped_set: set[str] = set()
    for ws_path in all_paths:
        result = fetched.get(ws_path)
        if result is None:
            content_bytes, sha = b"", hashlib.sha256(b"").hexdigest()
        else:
            content_bytes, sha = result
        rel = ws_path.lstrip("/")
        local_path = vault / rel
        _safe_write_bytes(local_path, content_bytes)
        dumped_set.add(ws_path)
        manifest.append(
            {
                "ws_path": ws_path,
                "local_path": str(local_path),
                "sha256": sha,
                "bytes": len(content_bytes),
                "rule_source": _classify_rule(ws_path),
            }
        )

    # 5b. /proc index files (README/AGENTS at any depth) — ALWAYS dumped,
    #     independent of world modes. The level-2 /proc record walk (stage
    #     2b) is gated off by default, so `/proc/<family>/README.md` would
    #     otherwise be lost (only the top-level `/proc/README.md` survives
    #     via the root tree). Use the harness Find RPC: it locates files by
    #     name in one recursive call and returns the REAL on-disk paths, so
    #     we don't guess casing (the read path is case-insensitive — probing
    #     name variants created duplicate vault files) and don't walk every
    #     record. Union a few name spellings (prod casing is inconsistent);
    #     Find returns real paths so duplicates fold by `set`. Under world
    #     modes these files arrive via stage 3b first and are skipped here.
    proc_index_paths: set[str] = set()
    for name in _PROC_INDEX_NAMES:
        try:
            res = vm.find(
                FindRequest(root="/proc", name=name, kind=NODE_KIND_FILE, limit=200)
            )
            proc_index_paths.update(res.paths)
        except Exception:
            continue
    proc_index_paths -= dumped_set
    if proc_index_paths:
        fetched_idx = _read_paths_parallel(
            harness_url, sorted(proc_index_paths), workers=READ_WORKERS
        )
        for p in sorted(proc_index_paths):
            r = fetched_idx.get(p)
            if r is None:
                continue  # vanished between find and read — skip
            content_bytes, sha = r
            local_path = vault / p.lstrip("/")
            _safe_write_bytes(local_path, content_bytes)
            dumped_set.add(p)
            manifest.append(
                {
                    "ws_path": p,
                    "local_path": str(local_path),
                    "sha256": sha,
                    "bytes": len(content_bytes),
                    "rule_source": _classify_rule(p),
                }
            )

    # 6. Rule 3 — transitive non-JSON cross-links from included docs.
    #    BFS by levels: collect every undumped non-JSON ref from the
    #    current frontier of docs, fetch them in ONE parallel batch
    #    (`_read_paths_parallel`), write them, then walk the
    #    newly-fetched docs to form the next level. Bounded by
    #    `_RULE3_MAX_FETCHES`. Source-of-truth for each ref's parent
    #    doc is recorded in `pre-bootstrap-manifest.json` so an
    #    operator can audit who pulled a file in.
    # Top-level workspace dirs (docs/bin/proc/run/uploads/…), read live from
    # the root tree rather than hardcoded — they scope the bare-path regex,
    # the root-relative link fix, and the directory-mention skip below.
    root_dirs = _top_level_dirs(root_tree_node)
    link_re = _build_link_re(root_dirs)
    rule3_added: list[str] = []
    rule3_scanned: set[str] = set()
    frontier: list[str] = sorted(
        p for p in dumped_set if Path(p).suffix.lower() in _DOC_EXTS
    )
    while frontier and len(rule3_added) < _RULE3_MAX_FETCHES:
        # 6a. Walk the frontier locally and collect refs (origin tracked
        #     so the first parent wins). Skip already-scanned docs and
        #     already-dumped refs.
        pending: dict[str, str] = {}  # ref → first parent that named it
        for doc in frontier:
            if doc in rule3_scanned:
                continue
            rule3_scanned.add(doc)
            local_doc = vault / doc.lstrip("/")
            try:
                text = local_doc.read_text(encoding="utf-8")
            except OSError:
                continue
            base_dir = os.path.dirname(doc) or "/"
            for ref in _extract_refs(text, base_dir, link_re, root_dirs):
                if ref in dumped_set or ref in pending:
                    continue
                if Path(ref).suffix.lower() == ".json":
                    continue  # rule 3 is non-JSON only
                # /bin/* are executables, not transitive docs — don't probe
                # them (every `/bin/<tool> ...` example in a doc is a dead
                # read). Also skip bare workspace-root dir mentions
                # (`/docs`, `/proc`, …) — directories, not files.
                if ref.startswith("/bin/") or ref.lstrip("/") in root_dirs:
                    continue
                pending[ref] = doc
        if not pending:
            break
        # 6b. Cap level-wide so a runaway scan can't blow past the budget.
        budget_left = _RULE3_MAX_FETCHES - len(rule3_added)
        if len(pending) > budget_left:
            pending = dict(list(pending.items())[:budget_left])
        # 6c. One parallel batch.
        fetched_refs = _read_paths_parallel(
            harness_url, list(pending), workers=READ_WORKERS
        )
        next_frontier: list[str] = []
        for ref, parent in pending.items():
            result = fetched_refs.get(ref)
            if result is None:
                continue
            content_bytes, sha = result
            local_target = vault / ref.lstrip("/")
            _safe_write_bytes(local_target, content_bytes)
            dumped_set.add(ref)
            manifest.append(
                {
                    "ws_path": ref,
                    "local_path": str(local_target),
                    "sha256": sha,
                    "bytes": len(content_bytes),
                    "rule_source": f"rule3:transitive-from {parent}",
                }
            )
            rule3_added.append(ref)
            if Path(ref).suffix.lower() in _DOC_EXTS:
                next_frontier.append(ref)
        frontier = next_frontier

    # 7. Rule 4 — one `__sample__.json` per `/proc/<family>` (uses the
    #    proc tree already fetched in stage 2b). Written under `.logs/`
    #    (NOT `vault/`): these are record-shape evidence for the PA
    #    world_refresh/world_create modes only; the executor never needs
    #    them. See `WORLD_SAMPLES_SUBDIR`.
    samples_root = world_samples_dir(task_dir)
    proc_samples: list[str] = []
    for family_node in proc_node.get("children") or []:
        if family_node.get("kind") != "NODE_KIND_DIR":
            continue
        fam_name = (family_node.get("name") or "").strip("/")
        if not fam_name:
            continue
        sample_name: str | None = None
        for child in family_node.get("children") or []:
            cname = child.get("name") or ""
            if child.get("kind") == "NODE_KIND_FILE" and cname.lower().endswith(".json"):
                sample_name = cname
                break
        if sample_name is None:
            continue
        src_path = f"/proc/{fam_name}/{sample_name}"
        r = _read_one(vm, src_path)
        if r is None:
            continue
        content_bytes, sha = r
        target = samples_root / "proc" / fam_name / "__sample__.json"
        _safe_write_bytes(target, content_bytes)
        manifest.append(
            {
                "ws_path": src_path,
                "local_path": str(target),
                "sha256": sha,
                "bytes": len(content_bytes),
                "rule_source": f"rule4:proc_sample[{fam_name}]",
            }
        )
        proc_samples.append(fam_name)

    # 8. Static instructions copied verbatim into task_dir root.
    _copy_static_instructions(static_instructions_dir, task_dir)

    manifest_doc = {
        "pre_bootstrap_version": PRE_BOOTSTRAP_VERSION,
        "timestamp": time.time(),
        "benchmark_id": benchmark_id,
        "task_id": task_id,
        "trial_id": trial_id,
        "files": manifest,
    }
    logs_dir = task_dir / LOGS_DIR_NAME
    logs_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = logs_dir / "pre-bootstrap-manifest.json"
    _safe_write_text(manifest_path, json.dumps(manifest_doc, indent=2))

    return PreBootstrapResult(
        task_dir=task_dir,
        vault_dir=vault,
        tree_path=tree_path,
        manifest_path=manifest_path,
        files_copied=len(manifest),
    )


# ── bin-help builder ────────────────────────────────────────────────────


@dataclass
class BinHelpResult:
    bin_help_dir: Path
    bin_help_hash: str
    tools: list[str] = field(default_factory=list)


def _list_bin_tools(bin_dir: Path) -> list[Path]:
    """Files without an extension under vault/bin/ are runtime tools."""
    if not bin_dir.is_dir():
        return []
    out = []
    for p in sorted(bin_dir.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix:
            continue
        out.append(p)
    return out


def _format_help_doc(*, tool: str, exit_code: int, stdout: str, stderr: str) -> str:
    header = (
        f"# /bin/{tool} --help\n"
        f"# bin-help contract: v{BIN_HELP_VERSION}\n"
        f"# exit_code: {exit_code}\n"
        "\n"
        "## stdout\n"
    )
    body_stdout = stdout if stdout.endswith("\n") else stdout + "\n"
    body_stderr = ""
    if stderr.strip():
        suffix = stderr if stderr.endswith("\n") else stderr + "\n"
        body_stderr = f"\n## stderr\n{suffix}"
    return f"{header}{body_stdout}{body_stderr}"


def _list_proc_families(vm) -> list[str]:
    """Live `/proc` family directory names (they vary per trial)."""
    try:
        res = vm.list(ListRequest(path="/proc"))
    except Exception:
        return []
    d = MessageToDict(res, preserving_proto_field_name=True)
    return [
        name
        for e in d.get("entries", [])
        if e.get("kind") == "NODE_KIND_DIR"
        and (name := (e.get("name") or "").strip("/"))
    ]


def _sample_proc_family(vm, harness_url: str, family: str) -> dict | None:
    """find() + parallel-read a representative record sample for one family.

    Returns `{"records", "total", "sampled", "truncated"}` or None when the
    family has no readable JSON records. Records are sampled evenly across the
    sorted path list so optional fields / enum values from every partition have
    a chance to appear. Our own `__sample__.json` fixtures (if any leaked in)
    are skipped by basename.
    """
    root = f"/proc/{family}"
    try:
        found = vm.find(
            FindRequest(
                root=root, name="", kind=NODE_KIND_FILE, limit=PROC_SCHEMA_FIND_LIMIT
            )
        )
    except Exception:
        return None
    fd = MessageToDict(found, preserving_proto_field_name=True)
    paths = sorted(
        p
        for p in fd.get("paths", [])
        if p.endswith(".json") and not p.rsplit("/", 1)[-1].startswith("__")
    )
    if not paths:
        return None
    total = len(paths)
    truncated = bool(fd.get("truncated"))
    if total > PROC_SCHEMA_SAMPLE_PER_FAMILY:
        step = total / PROC_SCHEMA_SAMPLE_PER_FAMILY
        idx = sorted({int(i * step) for i in range(PROC_SCHEMA_SAMPLE_PER_FAMILY)})
        sample_paths = [paths[i] for i in idx if i < total]
    else:
        sample_paths = paths
    fetched = _read_paths_parallel(harness_url, sample_paths, workers=READ_WORKERS)
    records: list[dict] = []
    for p in sample_paths:
        r = fetched.get(p)
        if r is None:
            continue
        content_bytes, _sha = r
        try:
            obj = json.loads(content_bytes.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            continue
        if isinstance(obj, dict):
            records.append(obj)
    if not records:
        return None
    return {
        "records": records,
        "total": total,
        "sampled": len(records),
        "truncated": truncated,
    }


def _recover_schema_from_proc(harness_url: str) -> str | None:
    """Reconstruct the warehouse schema doc from the live /proc projection.

    Bootstrap fallback used ONLY when `/bin/sql` is unavailable. Lists /proc
    families, samples each, and renders via `proc_schema`. Returns the rendered
    doc, or None when /proc is absent / unreadable (caller keeps the diagnostic
    placeholder). Inference is fully data-driven — no family/column names are
    hard-coded, so it tracks per-trial /proc renames.
    """
    vm = make_vm(harness_url)
    families = _list_proc_families(vm)
    if not families:
        return None
    samples: dict[str, dict] = {}
    for fam in families:
        s = _sample_proc_family(vm, harness_url, fam)
        if s:
            samples[fam] = s
    if not samples:
        return None
    return build_recovered_schema_doc(samples, note=PROC_SCHEMA_RECOVERY_NOTE)


def _build_sqlite_schema_doc(harness_url: str) -> str:
    """Build `bin-help/sqlite_schema.txt`.

    Primary path: the `/bin/sql` sqlite_schema discovery query (dev, and any
    prod runtime where the SQL cluster is up) → `format_from_csv`, byte-for-byte
    unchanged. When `/bin/sql` is unavailable — transport error, non-zero exit
    (the PROD MS SQL cluster outage), or an empty result — fall back to
    reconstructing the schema from the live /proc JSON projection
    (`_recover_schema_from_proc`). Only if that ALSO yields nothing do we write
    the diagnostic placeholder, so bootstrap stays robust either way and the
    agent always gets a usable family/field/join map.
    """
    vm = make_vm(harness_url)
    try:
        res = vm.exec(ExecRequest(path="/bin/sql", args=[SQLITE_SCHEMA_QUERY]))
    except Exception as exc:
        recovered = _recover_schema_from_proc(harness_url)
        if recovered:
            return recovered
        return (
            "# SQLite schema (warehouse DB) — query via /bin/sql\n"
            f"# [sqlite_schema fetch failed: {exc}]\n"
            "# [/proc recovery unavailable]\n"
            f"# Re-run: /bin/sql '{SQLITE_SCHEMA_QUERY}'\n"
        )

    exit_code = int(getattr(res, "exit_code", 0) or 0)
    stdout = res.stdout or ""
    stderr = res.stderr or ""
    if exit_code != 0:
        recovered = _recover_schema_from_proc(harness_url)
        if recovered:
            return recovered
        return (
            "# SQLite schema (warehouse DB) — query via /bin/sql\n"
            f"# [sqlite_schema query exit_code={exit_code}]\n"
            f"# stderr: {stderr.strip()}\n"
            "# [/proc recovery unavailable]\n"
            f"# Re-run: /bin/sql '{SQLITE_SCHEMA_QUERY}'\n"
        )

    if not parse_csv_rows(stdout):
        # SQL answered but produced no tables — try /proc before the placeholder.
        recovered = _recover_schema_from_proc(harness_url)
        if recovered:
            return recovered
    return format_from_csv(stdout)


def _compute_bin_help_hash(bin_help_dir: Path) -> str:
    """Hash the (relative_path, sha256(content)) list of help files."""
    entries: list[tuple[str, str]] = []
    for p in sorted(bin_help_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(bin_help_dir).as_posix()
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        entries.append((rel, sha))
    payload = json.dumps(
        {"version": BIN_HELP_VERSION, "entries": entries}, sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_bin_help(
    *,
    harness_url: str,
    task_dir: Path,
) -> BinHelpResult:
    """Build `bin-help/` for the current task directory.

    Tool `--help` calls fan out to EXEC_WORKERS threads; concurrency across
    trials is bounded by the dispatcher's worker semaphore (`--concurrency`).
    """
    bin_help_dir = task_dir / "bin-help"
    if bin_help_dir.exists():
        shutil.rmtree(bin_help_dir)
    bin_help_dir.mkdir(parents=True, exist_ok=True)

    vault_bin = task_dir / "vault" / "bin"
    tools = _list_bin_tools(vault_bin)
    captured: list[str] = []

    def _exec_one(rel: str) -> tuple[str, int, str, str]:
        ws_path = f"/bin/{rel}"
        worker_vm = make_vm(harness_url)
        try:
            res = worker_vm.exec(ExecRequest(path=ws_path, args=["--help"]))
            exit_code = int(getattr(res, "exit_code", 0) or 0)
            stdout = res.stdout or ""
            stderr = res.stderr or ""
        except Exception as exc:
            exit_code = -1
            stdout = ""
            stderr = f"[bin-help exec error: {exc}]"
        return rel, exit_code, stdout, stderr

    rels = [tp.relative_to(vault_bin).as_posix() for tp in tools]
    with concurrent.futures.ThreadPoolExecutor(max_workers=EXEC_WORKERS) as pool:
        for rel, exit_code, stdout, stderr in pool.map(_exec_one, rels):
            doc = _format_help_doc(
                tool=rel, exit_code=exit_code, stdout=stdout, stderr=stderr
            )
            out_path = bin_help_dir / f"{rel}.help.txt"
            _safe_write_text(out_path, doc)
            captured.append(rel)

    schema_doc = _build_sqlite_schema_doc(harness_url)
    _safe_write_text(bin_help_dir / SQLITE_SCHEMA_FILE, schema_doc)

    bin_help_hash = _compute_bin_help_hash(bin_help_dir)

    logs_dir = task_dir / LOGS_DIR_NAME
    logs_dir.mkdir(parents=True, exist_ok=True)
    local_manifest = logs_dir / "bin-help-manifest.json"
    _safe_write_text(
        local_manifest,
        json.dumps(
            {
                "bin_help_version": BIN_HELP_VERSION,
                "bin_help_hash": bin_help_hash,
                "tools": captured,
            },
            indent=2,
        ),
    )

    return BinHelpResult(
        bin_help_dir=bin_help_dir,
        bin_help_hash=bin_help_hash,
        tools=captured,
    )


# ── Trial-static prerender (identity + sim-date) ────────────────────────


@dataclass
class TrialPrerender:
    """Output of `/bin/id` and `/bin/date` captured once at trial start.

    Substituted into instruction unit content.md by the resolver
    (`{{TRIAL_IDENTITY}}` / `{{TRIAL_DATE}}`) so the agent reads identity
    and sim-date inline without spending a turn on `ws.id()` / `ws.date()`.
    Both values are constant for the duration of the trial.
    """

    identity: str
    date: str


def fetch_trial_prerender(harness_url: str) -> TrialPrerender:
    vm = make_vm(harness_url)

    def _run(path: str) -> str:
        try:
            res = vm.exec(ExecRequest(path=path, args=[]))
            exit_code = int(getattr(res, "exit_code", 0) or 0)
            stdout = (res.stdout or "").rstrip("\n")
            stderr = (res.stderr or "").rstrip("\n")
        except Exception as exc:
            return f"[prerender exec error: {exc}]"
        if exit_code != 0:
            return f"[exit_code={exit_code}; stderr: {stderr}]"
        return stdout

    return TrialPrerender(identity=_run("/bin/id"), date=_run("/bin/date"))


# ── Optional SQL table dump (opt-in via --dump-sql-rows) ────────────────


@dataclass
class DumpSqlResult:
    dump_sql_dir: Path
    tables_dumped: list[str] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)


def _write_table_csv(path: Path, rows: list[dict]) -> int:
    """Write rows as CSV using union-of-keys column order. Returns row count."""
    if not rows:
        path.write_text("", encoding="utf-8")
        return 0
    cols: list[str] = []
    seen: set[str] = set()
    for r in rows:
        for k in r:
            if k not in seen:
                seen.add(k)
                cols.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in cols})
    return len(rows)


def dump_sql_tables(
    *,
    harness_url: str,
    task_dir: Path,
    limit: int,
) -> DumpSqlResult:
    """Dump first `limit` rows of each user table via `ws.sql_rows`.

    Writes one CSV per table to `task_dir/dump_sql/<table>.csv` plus a
    `manifest.json` with per-table `total_rows` / `dumped_rows` / `truncated`
    so callers can see at a glance which tables were capped at `limit`.

    Reuses `Workspace.sql_rows` from `static-instructions/workspace.py` —
    the harness 100-row cap and pagination are handled there.
    """
    static_dir = Path(__file__).resolve().parent.parent / "static-instructions"
    if str(static_dir) not in sys.path:
        sys.path.insert(0, str(static_dir))
    from workspace import Workspace  # noqa: PLC0415

    dump_dir = task_dir / "dump_sql"
    if dump_dir.exists():
        shutil.rmtree(dump_dir)
    dump_dir.mkdir(parents=True, exist_ok=True)

    # Workspace ctor requires an answer_path but only `ws.answer()` touches
    # it; we never call answer here. Point at a never-written sentinel.
    dummy_answer = str(task_dir / LOGS_DIR_NAME / "dump_sql-unused-answer.json")

    errors: list[dict] = []
    try:
        listing_ws = Workspace(harness_url=harness_url, answer_path=dummy_answer)
        schema_res = listing_ws.sql_rows(
            "SELECT name FROM sqlite_schema "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name",
            limit=1000,
        )
        tables = [
            r["name"] for r in schema_res["rows"]
            if isinstance(r, dict) and isinstance(r.get("name"), str)
        ]
    except Exception as exc:
        errors.append({"step": "list_tables", "error": str(exc)})
        _safe_write_text(
            dump_dir / "manifest.json",
            json.dumps(
                {"limit": limit, "tables": {}, "errors": errors},
                indent=2,
                ensure_ascii=False,
            ),
        )
        return DumpSqlResult(dump_sql_dir=dump_dir, tables_dumped=[], errors=errors)

    def _process_one(name: str) -> tuple[str, dict, list[dict]]:
        # Per-thread Workspace so the underlying SDK client + retry layer
        # are not shared across workers.
        worker_ws = Workspace(harness_url=harness_url, answer_path=dummy_answer)
        local_errors: list[dict] = []
        total: int | None = None
        try:
            count_res = worker_ws.sql_rows(
                f"SELECT COUNT(*) AS c FROM {name}", limit=1
            )
            if count_res["rows"]:
                total = int(count_res["rows"][0].get("c") or 0)
        except Exception as exc:
            local_errors.append({"table": name, "step": "count", "error": str(exc)})
        dumped_count = 0
        truncated_flag = False
        try:
            rows_res = worker_ws.sql_rows(f"SELECT * FROM {name}", limit=limit)
            dumped_count = _write_table_csv(
                dump_dir / f"{name}.csv", rows_res["rows"]
            )
            truncated_flag = bool(rows_res["truncated"])
        except Exception as exc:
            local_errors.append({"table": name, "step": "dump", "error": str(exc)})
        info = {
            "total_rows": total,
            "dumped_rows": dumped_count,
            "truncated": truncated_flag
            or (total is not None and total > dumped_count),
        }
        return name, info, local_errors

    table_manifest: dict[str, dict] = {}
    dumped: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=EXEC_WORKERS) as pool:
        for name, info, errs in pool.map(_process_one, tables):
            table_manifest[name] = info
            errors.extend(errs)
            if not any(e.get("step") == "dump" for e in errs):
                dumped.append(name)

    manifest: dict = {"limit": limit, "tables": table_manifest}
    if errors:
        manifest["errors"] = errors
    _safe_write_text(
        dump_dir / "manifest.json",
        json.dumps(manifest, indent=2, ensure_ascii=False),
    )
    return DumpSqlResult(
        dump_sql_dir=dump_dir,
        tables_dumped=dumped,
        errors=errors,
    )
