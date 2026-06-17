# world_baseline v0003

- created_at: `2026-05-28T14:54:53+00:00`
- created_by: `process_architect`
- parent: `v0002`
- no_semantic_change: `False`

## Rationale

world_refresh advance from v0002

## Files tracked
- `workspace:/AGENTS.MD` — sha256 `f612b7b2144e…`, 2354 bytes
- `workspace:/docs/README.md` — sha256 `979477da9930…`, 6068 bytes
- `workspace:/run/actions/README.md` — sha256 `2c25d7da9159…`, 64 bytes
- `workspace:/bin/README.md` — sha256 `1fc35ac2bc73…`, 696 bytes
- `bin_help:sqlite_schema.txt` — sha256 `56106491f856…`, 6850 bytes
- `bin_help:checkout.help.txt` — sha256 `65ef4279c83f…`, 101 bytes
- `bin_help:date.help.txt` — sha256 `9fa7f21898b9…`, 81 bytes
- `bin_help:discount.help.txt` — sha256 `0ca83d3f895e…`, 234 bytes
- `bin_help:id.help.txt` — sha256 `9ac6a87201e7…`, 131 bytes
- `bin_help:payments.help.txt` — sha256 `be7283368435…`, 356 bytes
- `bin_help:sql.help.txt` — sha256 `a66a4727ffea…`, 1728 bytes

## Diff vs parent

See `diff.patch`.

## Backfill note

`workspace:/bin/README.md` was added to the tracked set by a manual backfill (`.tasks/task-029/backfill_bin_readme.py`) after it was found to drift between the v0003 and v0004 worlds without ever being in `world.json` — so it never reached `snapshot/`/`manifest.json`/`diff.patch` (only `vault-diff.patch` caught it). The bytes recorded here are the live values from each version's `vault/bin/README.md`; only this one file's tracking metadata was retrofitted.
