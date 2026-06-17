# bp_fraud_risk_review v0002

- mode: `failure_fix`
- created_by: `codex`
- created_at: `2026-05-26T10:29:46+00:00`
- parent: `v0001`

## Rationale

Make fraud/risk cohort discovery precision-first by adding a hard-vs-soft gate, per-record hard-evidence mapping, safer incident membership semantics, and clearer geo-axis interpretation. This keeps complete-set behavior only after candidates pass the hard gate and avoids soft-only data-decoy over-inclusion.

## Rollback

Retire v0002 and fall back to v0001 if the hard gate causes systematic misses of true risk cohorts that only the older recall-biased process found.

## Dependencies
- `workspace:/docs/payments/3ds.md` — Defines payment workflow-state invariants used in fraud/risk checks.
- `bin_help:sql.help.txt` — SQL interface and schema-discovery contract for risk queries.
- `sql_table:payments` — Primary risk table, fingerprints, timestamps, status, observed coordinates, and 3DS columns.
- `sql_table:customers` — Customer identity and home-coordinate context for distinguishing remote shopping from observed-location fraud.
- `sql_table:stores` — Store location axis used for geo/time anomaly checks.
- `sql_table:baskets` — Basket/customer/store joins and archive context used in risk checks.
- `sql_table:payment_lines` — Line-level amount reconciliation for payment anomaly checks.
- `sql_table:products` — Catalogue price joins for amount/line checks.
