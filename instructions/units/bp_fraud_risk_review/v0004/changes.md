# bp_fraud_risk_review v0004

- mode: `failure_fix`
- created_by: `codex`
- created_at: `2026-05-26T13:33:55+00:00`
- parent: `v0003`

## Rationale

Keep the v0003 hard gate, mandatory sweep, and union contract, while pinning query correctness with scope immutability, observed-travel and sliding-burst contracts, validated-zero ledger fields, and compact reusable risk investigation Tricks.

## Rollback

Retire v0004 and fall back to v0003 if the canonical query shapes or broader Tricks cause overfitting, excessive prompt weight, or false-positive unions.

## Dependencies
- `workspace:/docs/payments/3ds.md` — Defines payment workflow-state invariants used in fraud/risk checks.
- `bin_help:sql.help.txt` — SQL interface and schema-discovery contract for risk queries.
- `sql_table:payments` — Primary risk table, fingerprints, timestamps, status, observed coordinates, and 3DS columns.
- `sql_table:customers` — Customer identity and home-coordinate context for distinguishing remote shopping from observed-location fraud.
- `sql_table:stores` — Store location axis used for geo/time anomaly checks.
- `sql_table:baskets` — Basket/customer/store joins and archive context used in risk checks.
- `sql_table:basket_lines` — Basket resource lines for quantity/resource reconciliation.
- `sql_table:payment_lines` — Line-level amount reconciliation for payment anomaly checks.
- `sql_table:products` — Catalogue price joins for amount/line checks.
- `sql_table:inventory` — Reserve/availability arithmetic and store/SKU resource axis for broader risk checks.
- `sql_table:returns` — Return/payment/basket/customer workflow joins for broader risk checks.
