# bp_fraud_risk_review v0003

- mode: `failure_fix`
- created_by: `codex`
- created_at: `2026-05-26T12:09:38+00:00`
- parent: `v0002`

## Rationale

Keep the v0002 precision hard gate, but add a mandatory hard-sweep ledger, an explicit stationary single-actor multi-store burst shape, a missing-MO guard, and a stronger union contract so every hard-supported cluster in scope reaches refs.

## Rollback

Retire v0003 and fall back to v0002 if mandatory hard sweep causes broad false-positive unions or systematic over-inclusion of soft-only clusters.

## Dependencies
- `workspace:/docs/payments/3ds.md` — Defines payment workflow-state invariants used in fraud/risk checks.
- `bin_help:sql.help.txt` — SQL interface and schema-discovery contract for risk queries.
- `sql_table:payments` — Primary risk table, fingerprints, timestamps, status, observed coordinates, and 3DS columns.
- `sql_table:customers` — Customer identity and home-coordinate context for distinguishing remote shopping from observed-location fraud.
- `sql_table:stores` — Store location axis used for geo/time anomaly checks.
- `sql_table:baskets` — Basket/customer/store joins and archive context used in risk checks.
- `sql_table:payment_lines` — Line-level amount reconciliation for payment anomaly checks.
- `sql_table:products` — Catalogue price joins for amount/line checks.
