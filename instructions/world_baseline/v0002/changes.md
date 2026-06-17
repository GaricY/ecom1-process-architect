# world_baseline v0002

- created_at: `2026-05-22T02:15:37+00:00`
- created_by: `process_architect`
- parent: `v0001`
- no_semantic_change: `False`

## Rationale

world_refresh advance from v0001

## Files tracked
- `workspace:/AGENTS.MD` — sha256 `f612b7b2144e…`, 2354 bytes
- `workspace:/docs/README.md` — sha256 `405181535569…`, 5715 bytes
- `workspace:/run/actions/README.md` — sha256 `2c25d7da9159…`, 64 bytes
- `bin_help:sqlite_schema.txt` — sha256 `7d2731419043…`, 6669 bytes
- `bin_help:checkout.help.txt` — sha256 `65ef4279c83f…`, 101 bytes (back-fill — see below)
- `bin_help:date.help.txt` — sha256 `9fa7f21898b9…`, 81 bytes (back-fill — see below)
- `bin_help:discount.help.txt` — sha256 `0ca83d3f895e…`, 234 bytes (back-fill — see below)
- `bin_help:id.help.txt` — sha256 `9ac6a87201e7…`, 131 bytes (back-fill — see below)
- `bin_help:payments.help.txt` — sha256 `be7283368435…`, 356 bytes (back-fill — see below)
- `bin_help:sql.help.txt` — sha256 `a66a4727ffea…`, 1728 bytes (back-fill — see below)

## Diff vs parent

See `diff.patch`. Note: `diff.patch` predates the bin-help back-fill, so
it does not show the `payments.help.txt` change (refund verbs added
v0001→v0002, 199→356 bytes) — that delta is visible by diffing the two
baselines' `snapshot/bin-help/payments.help.txt` directly.

## Back-fill — bin-help command help (`*.help.txt`)

Added `checkout/date/discount/id/payments/sql.help.txt` to the
snapshot + manifest after the fact, when `world.json` was extended to
track the full `/bin/*` tool surface (not just `sqlite_schema.txt`).
Bytes taken from this baseline's own world_refresh trial dump
(`20260522-050537/0001-t01-…-process-architect-world-refresh-v0001/bin-help/`),
so each file reflects the world as it actually was at v0002. Only
`payments.help.txt` differs from v0001 (the organizer added the
`approve-refund` / `refund` verbs — the same change that drove this
baseline's `/AGENTS.MD` + `/docs/README.md` advance). These files stay
pinned per-unit as well; the extension only adds world-layer coverage.
