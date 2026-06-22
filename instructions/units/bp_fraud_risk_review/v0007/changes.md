# bp_fraud_risk_review v0007

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-30T09:37:50+00:00`
- parent: `v0006`

## Rationale

/bin/sql is down so the SQL window-function scan shapes are re-expressed as Python-over-/proc-JSON scans read via /bin/jq|cat; tables/columns renamed (payment_ledger.created_at, observed_lat/observed_lon, archived, status; three_ds moved to payment_three_ds; payment_lines; carts/cart_lines; return_workflows; locations/location_inventory; catalog); the customer_accounts table was removed so customer home_latitude/home_longitude no longer exist and the observed-vs-home axis is dropped; /proc/*/README.md semantics move into the schema.

## Rollback

Restore v0006 content (SQL query shapes, payment_transactions/customer_accounts column names, observed-vs-home axis, /proc README dependencies).

## Dependencies
- `workspace:/docs/payments/3ds.md` — Legitimate 3DS workflow-state transitions used for payment invariant checks.
- `bin_help:jq.help.txt` — JSON read tool used for the scans now that /bin/sql is unavailable.
- `bin_help:cat.help.txt` — Raw record read tool for risk scans.
- `sql_table:payment_ledger` — Primary risk record: fingerprints, created_at, status, observed_lat/observed_lon, archived.
- `sql_table:payment_three_ds` — status/attempts/max_attempts/retry_after for workflow-state invariants.
- `sql_table:payment_lines` — Line-level reconciliation (quantity, unit_price_cents) for amount anomalies.
- `sql_table:carts` — Cart/customer/store joins and archive context.
- `sql_table:cart_lines` — Resource lines for quantity/resource reconciliation.
- `sql_table:return_workflows` — Return/payment workflow joins.
- `sql_table:locations` — Store coordinates axis for geo context.
- `sql_table:location_inventory` — Reserve/availability arithmetic and store/SKU resource axis.
- `sql_table:catalog` — Price joins for amount/line checks.
