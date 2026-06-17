# bp_product_discovery v0009

- mode: `refresh`
- created_by: `codex`
- created_at: `2026-05-26T08:28:15+00:00`
- parent: `v0008`

## Rationale

Add the shared policy_update_scan handoff and replace product_discovery local catalogue-count dated-update substeps with helper delegation, avoiding contradictory operating-day semantics while preserving catalogue/inventory logic.

## Rollback

Create a new version from v0008 if the delegated catalogue-count update rule misses required dated reporting updates.

## Dependencies
- `bin_help:sql.help.txt` — Defines catalogue/inventory table shapes and SQL interface used by this BP.
- `bin_help:date.help.txt` — Trusted date provider still needed when product count/update handling invokes policy_update_scan.
- `bin_help:id.help.txt` — Actor identity pulled at session start.
