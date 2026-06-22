# bp_fraud_risk_review v0008

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-22T00:02:07+00:00`
- parent: `v0007`

## Rationale

SQL is unavailable (/bin/sql PROD cluster down); the schema is the reconstructed /proc projection. Re-derived to read /proc/payment-ledger JSON and aggregate in Python, with renamed fields (created_at, status, observed_lat/observed_lon, archived bool, three_ds object) and family renames (carts/locations/return-workflows/catalog). Dropped the customer-home-coordinate axis because no customer-account record exists. Hard-sweep methodology preserved.

## Rollback

Restore bp_fraud_risk_review v0007 content with its SQL queries and customer_accounts/stores/shopping_baskets dependencies.

## Dependencies
- `workspace:/docs/payments/3ds.md` — Legitimate 3DS workflow-state transitions used for payment invariant checks.
- `sql_table:payment-ledger` — Primary risk record: fingerprints, created_at, status, observed_lat/lon, amount_cents, lines, three_ds, archived, join keys.
- `sql_table:carts` — Basket/customer/store joins and archive context.
- `sql_table:locations` — Branch lat/lon and inventory (on_hand/reserved) for store-distance and reserve arithmetic.
- `sql_table:return-workflows` — Return/payment workflow joins.
- `sql_table:catalog` — price_cents for amount/line reconciliation.
