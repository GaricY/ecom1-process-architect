# bp_availability v0002

- mode: `refresh`
- created_by: `human`
- created_at: `2026-05-30T09:46:43+00:00`
- parent: `v0001`

## Rationale

Drop dead sql_table deps. /bin/sql cluster is down on ecom1-prod, so bin-help/sqlite_schema.txt is the outage error and every sql_table dep is permanently stale, flooding attention/unit-diffs (run 20260530-123952/0001-t001). The warehouse is now read from the /proc file projection (ws.proc/read_json/jq, executor_core v0014), so table-name deps no longer model a real dependency. Content unchanged; only the structured dependency contract drops the sql_table entries (kept: workspace docs + command bin-helps). A future refresh/world_refresh can re-add table deps if /bin/sql recovers.

## Rollback

Revert to v0001 (bp_admin rollback bp_availability --from v0001, or retire the new version) to restore the sql_table deps if /bin/sql recovers and table-keyed staleness is wanted.

## Dependencies
- `workspace:/docs/availability-checks.md` — Same-day availability formula, missing-SKU rule, incoming-stock + due-within rules, read-only guarantee, and the inventory-export contract.
- `bin_help:availability.help.txt` — availability <store_record_path|-> <sku>... ; max(on_hand-reserved,0), missing SKU -> 0.
- `bin_help:jq.help.txt` — JSON read tool for store/inventory/incoming/catalog rows now that /bin/sql is unavailable.
- `bin_help:cat.help.txt` — Raw record read tool for inventory JSON.
- `bin_help:date.help.txt` — Used when the request imposes a date/window or future-date export columns.
