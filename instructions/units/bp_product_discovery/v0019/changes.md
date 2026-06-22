# bp_product_discovery v0019

- mode: `refresh`
- created_by: `human`
- created_at: `2026-05-30T09:46:45+00:00`
- parent: `v0018`

## Rationale

Drop dead sql_table deps. /bin/sql cluster is down on ecom1-prod, so bin-help/sqlite_schema.txt is the outage error and every sql_table dep is permanently stale, flooding attention/unit-diffs (run 20260530-123952/0001-t001). The warehouse is now read from the /proc file projection (ws.proc/read_json/jq, executor_core v0014), so table-name deps no longer model a real dependency. Content unchanged; only the structured dependency contract drops the sql_table entries (kept: workspace docs + command bin-helps). A future refresh/world_refresh can re-add table deps if /bin/sql recovers.

## Rollback

Revert to v0018 (bp_admin rollback bp_product_discovery --from v0018, or retire the new version) to restore the sql_table deps if /bin/sql recovers and table-keyed staleness is wanted.

## Dependencies
- `workspace:/docs/catalogue-lookup.md` — Catalogue resolution rule (resolve to exactly one product, else clarify and cite candidate SKUs); replaces the removed /docs/README.md catalogue reporting rule.
- `bin_help:jq.help.txt` — JSON read tool for catalogue/store data now that /bin/sql is unavailable.
- `bin_help:cat.help.txt` — Raw record read tool for catalogue/store JSON.
- `bin_help:date.help.txt` — Operating-day source for any dated catalogue reporting rule.
- `bin_help:id.help.txt` — Actor identity pulled at session start.
