# bp_fraud_risk_review v0001

- mode: `initial_migration`
- created_by: `codex`
- created_at: `2026-05-26T08:22:43+00:00`

## Rationale

Extract fraud/risk/anomaly discovery rules from bp_refs_and_submission into a dedicated BP. It preserves the complete-set, multi-axis, density-refinement, pair/group, and temporal-window rules without making general refs carry task-shaped fraud methodology.

## Rollback

Remove this unit from registry and restore the v0011 fraud section if dedicated fraud routing misses known archived-payment cohorts.

## Dependencies
- `workspace:/docs/payments/3ds.md` — Defines payment workflow-state invariants used in fraud/risk checks.
- `bin_help:sql.help.txt` — SQL interface and schema-discovery contract for risk queries.
- `sql_table:payments` — Primary risk table and payment anomaly columns.
- `sql_table:stores` — Store location axis used for geo/time anomaly checks.
- `sql_table:baskets` — Basket/customer/store joins and archive context used in risk checks.
- `sql_table:payment_lines` — Line-level amount reconciliation for payment anomaly checks.
- `sql_table:products` — Catalogue price joins for amount/line checks.
