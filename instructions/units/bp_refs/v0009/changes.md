# bp_refs v0009

- mode: `refresh`
- created_by: `human`
- created_at: `2026-05-30T09:46:45+00:00`
- parent: `v0008`

## Rationale

Drop dead sql_table deps. /bin/sql cluster is down on ecom1-prod, so bin-help/sqlite_schema.txt is the outage error and every sql_table dep is permanently stale, flooding attention/unit-diffs (run 20260530-123952/0001-t001). The warehouse is now read from the /proc file projection (ws.proc/read_json/jq, executor_core v0014), so table-name deps no longer model a real dependency. Content unchanged; only the structured dependency contract drops the sql_table entries (kept: workspace docs + command bin-helps). A future refresh/world_refresh can re-add table deps if /bin/sql recovers.

## Rollback

Revert to v0008 (bp_admin rollback bp_refs --from v0008, or retire the new version) to restore the sql_table deps if /bin/sql recovers and table-keyed staleness is wanted.

## Dependencies
- `workspace:/docs/security.md` — Cross-boundary rule and personal-information disclosure boundary.
- `workspace:/docs/attachments.md` — Defines /uploads as the request-named input-artifact root for class-1 grounding.
- `bin_help:id.help.txt` — Actor output shape for customer/employee/guest branching.
