# bp_privacy_and_disclosure v0005

- mode: `refresh`
- created_by: `human`
- created_at: `2026-05-30T09:46:44+00:00`
- parent: `v0004`

## Rationale

Drop dead sql_table deps. /bin/sql cluster is down on ecom1-prod, so bin-help/sqlite_schema.txt is the outage error and every sql_table dep is permanently stale, flooding attention/unit-diffs (run 20260530-123952/0001-t001). The warehouse is now read from the /proc file projection (ws.proc/read_json/jq, executor_core v0014), so table-name deps no longer model a real dependency. Content unchanged; only the structured dependency contract drops the sql_table entries (kept: workspace docs + command bin-helps). A future refresh/world_refresh can re-add table deps if /bin/sql recovers.

## Rollback

Revert to v0004 (bp_admin rollback bp_privacy_and_disclosure --from v0004, or retire the new version) to restore the sql_table deps if /bin/sql recovers and table-keyed staleness is wanted.

## Dependencies
- `workspace:/docs/security.md` — Personal-information cross-boundary rule and the employee-contact non-disclosure rule.
- `bin_help:id.help.txt` — Actor output shape for ownership/disclosure branching.
