# bp_discount v0012

- mode: `refresh`
- created_by: `human`
- created_at: `2026-05-30T09:46:44+00:00`
- parent: `v0011`

## Rationale

Drop dead sql_table deps. /bin/sql cluster is down on ecom1-prod, so bin-help/sqlite_schema.txt is the outage error and every sql_table dep is permanently stale, flooding attention/unit-diffs (run 20260530-123952/0001-t001). The warehouse is now read from the /proc file projection (ws.proc/read_json/jq, executor_core v0014), so table-name deps no longer model a real dependency. Content unchanged; only the structured dependency contract drops the sql_table entries (kept: workspace docs + command bin-helps). A future refresh/world_refresh can re-add table deps if /bin/sql recovers.

## Rollback

Revert to v0011 (bp_admin rollback bp_discount --from v0011, or retire the new version) to restore the sql_table deps if /bin/sql recovers and table-keyed staleness is wanted.

## Dependencies
- `workspace:/docs/discounts.md` — Gate set, the 18000-cent/8-percent/4-percent tiers, reason-code enum, non-authority bait, the line-eligibility bridge into checkout, and the manager-store-match gate.
- `workspace:/docs/checkout.md` — The line-eligibility (same-day availability) gate the discount policy applies.
- `workspace:/docs/security.md` — Identity gate applied via identity_and_auth.
- `bin_help:discount.help.txt` — Signature <basket_id> <percent> <reason_code> <issuer_id> and the no-policy-checks disclaimer.
- `bin_help:availability.help.txt` — Same-day availability for the per-line eligibility re-check.
