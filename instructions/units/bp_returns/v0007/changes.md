# bp_returns v0007

- mode: `refresh`
- created_by: `human`
- created_at: `2026-05-30T09:46:45+00:00`
- parent: `v0006`

## Rationale

Drop dead sql_table deps. /bin/sql cluster is down on ecom1-prod, so bin-help/sqlite_schema.txt is the outage error and every sql_table dep is permanently stale, flooding attention/unit-diffs (run 20260530-123952/0001-t001). The warehouse is now read from the /proc file projection (ws.proc/read_json/jq, executor_core v0014), so table-name deps no longer model a real dependency. Content unchanged; only the structured dependency contract drops the sql_table entries (kept: workspace docs + command bin-helps). A future refresh/world_refresh can re-add table deps if /bin/sql recovers.

## Rollback

Revert to v0006 (bp_admin rollback bp_returns --from v0006, or retire the new version) to restore the sql_table deps if /bin/sql recovers and table-keyed staleness is wanted.

## Dependencies
- `workspace:/docs/returns.md` — Both gate sets, refund_manager role, the approved->refund_pending->closed sequence, the /bin/refund invocations, and the prohibition on editing return files by hand.
- `workspace:/docs/security.md` — Identity/ownership/role rule named verbatim as a prerequisite by returns.md.
- `bin_help:refund.help.txt` — Tool signatures for approve <return_id> and close <return_id> (replaces the retired /bin/payments approve-refund|refund).
- `bin_help:payments.help.txt` — Confirms /bin/payments no longer carries refund verbs (only recover-3ds).
