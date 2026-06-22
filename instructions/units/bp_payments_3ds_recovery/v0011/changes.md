# bp_payments_3ds_recovery v0011

- mode: `refresh`
- created_by: `human`
- created_at: `2026-05-30T09:46:44+00:00`
- parent: `v0010`

## Rationale

Drop dead sql_table deps. /bin/sql cluster is down on ecom1-prod, so bin-help/sqlite_schema.txt is the outage error and every sql_table dep is permanently stale, flooding attention/unit-diffs (run 20260530-123952/0001-t001). The warehouse is now read from the /proc file projection (ws.proc/read_json/jq, executor_core v0014), so table-name deps no longer model a real dependency. Content unchanged; only the structured dependency contract drops the sql_table entries (kept: workspace docs + command bin-helps). A future refresh/world_refresh can re-add table deps if /bin/sql recovers.

## Rollback

Revert to v0010 (bp_admin rollback bp_payments_3ds_recovery --from v0010, or retire the new version) to restore the sql_table deps if /bin/sql recovers and table-keyed staleness is wanted.

## Dependencies
- `workspace:/docs/payments/3ds.md` — Full gate set, the customer-identity gate, retry_after/3ds-status1 semantics, the 2-attempt cap, the recover-3ds invocation, and the security.md+checkout.md prerequisite line.
- `workspace:/docs/checkout.md` — Prerequisite policy that 3DS recovery defers to.
- `workspace:/docs/security.md` — Identity/cross-boundary rule named in the 3DS prerequisite line.
- `bin_help:payments.help.txt` — Tool signature; this BP authorises recover-3ds only (refund subcommands have moved off this binary).
- `bin_help:date.help.txt` — Trusted clock for retry_after / lockout comparison.
