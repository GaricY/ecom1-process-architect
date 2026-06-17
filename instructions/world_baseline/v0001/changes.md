# world_baseline v0001

- created_at: `2026-05-22T01:43:14+00:00`
- created_by: `bp_admin world-baseline init`
- parent: `none`
- no_semantic_change: `False`

## Rationale

Manual seed from trial dump at /home/garic/proj/bitgn/.runs/ecom/20260521-151002/0001-t01-vm2-LxJEegubLZRKBGa78CiDWn4vMLC. Pre-drift baseline so world_refresh PA can diff against upstream evolution.

## Files tracked
- `workspace:/AGENTS.MD` — sha256 `c4457da9b936…`, 2302 bytes
- `workspace:/docs/README.md` — sha256 `927472bd8778…`, 5508 bytes
- `workspace:/run/actions/README.md` — sha256 `2c25d7da9159…`, 64 bytes
- `bin_help:sqlite_schema.txt` — sha256 `7d2731419043…`, 6669 bytes (post-patch — see below)
- `bin_help:checkout.help.txt` — sha256 `65ef4279c83f…`, 101 bytes (back-fill — see below)
- `bin_help:date.help.txt` — sha256 `9fa7f21898b9…`, 81 bytes (back-fill — see below)
- `bin_help:discount.help.txt` — sha256 `0ca83d3f895e…`, 234 bytes (back-fill — see below)
- `bin_help:id.help.txt` — sha256 `9ac6a87201e7…`, 131 bytes (back-fill — see below)
- `bin_help:payments.help.txt` — sha256 `0cecccea27d9…`, 199 bytes (back-fill — see below)
- `bin_help:sql.help.txt` — sha256 `a66a4727ffea…`, 1728 bytes (back-fill — see below)

## Diff vs parent

(empty — initial seed or no semantic change)

## Manual patch — sqlite_schema.txt

Replaced `bin-help/sqlite_schema.txt` snapshot + manifest sha256 with
the current bytes from a recent trial dump
(`20260522-043652/0001-t01-.../bin-help/sqlite_schema.txt`, sha
`7d2731419043…`). Reason: the drift between the seed task_dir's
schema (`e57d8789396b…`) and current was caused by our own
`orchestrator/sql_schema.py` change (task-011 commit 5915aaa), not
upstream benchmark evolution. Without this patch the first
`world_refresh` experiment would report a spurious schema drift
alongside the real returns/refunds drift in `/AGENTS.MD` +
`/docs/README.md`.

## Back-fill — bin-help command help (`*.help.txt`)

Added `checkout/date/discount/id/payments/sql.help.txt` to the
snapshot + manifest after the fact, when `world.json` was extended to
track the full `/bin/*` tool surface (not just `sqlite_schema.txt`).
Bytes taken from this baseline's own seed trial dump
(`20260521-151002/0001-t01-vm2-LxJEegubLZRKBGa78CiDWn4vMLC/bin-help/`),
so each file reflects the world as it actually was at v0001. These
files stay pinned per-unit as well — the extension only adds world-layer
coverage, it does not strip the existing unit dependencies.
