# bp_index v0009

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-22T00:02:07+00:00`
- parent: `v0008`

## Rationale

Routing rebuilt for the current world: SQL is dead (read /proc, families renamed), account-recovery and OS/tooling-workaround domains removed, refund tool moved to /bin/refund, and three new domains added (availability/inventory, dispatch planning, purchase-request crosslist). Added the employee-on-customer-action unsupported principle (/docs/employees.md), the staff-contact privacy principle, the basket item-edit mutation, and the unsupported-system rule. Links the three new render paths so the validator's substring check passes.

## Rollback

Restore bp_index v0008 content; the old routing table, the SQL-based product_discovery row, the account-recovery and os-tooling rows, and the /bin/payments refund routes return.
