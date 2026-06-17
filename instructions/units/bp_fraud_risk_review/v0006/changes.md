# bp_fraud_risk_review v0006

- mode: `world_refresh`
- created_by: `codex`
- created_at: `2026-05-29T11:30:59+00:00`
- parent: `v0005`

## Rationale

Add proc README semantics for archived payments, observed/home/store coordinates, and opaque fingerprints; keep distance-only signals soft and avoid treating archived missing baskets as hard mismatches.

## Rollback

Revert to v0005 if the added semantics over-constrain fraud cohort discovery or conflict with a future risk policy.

## Dependencies
- `workspace:/docs/payments/3ds.md` — Legitimate 3DS workflow-state transitions used for payment workflow-state invariant checks.
- `sql_table:payment_transactions` — Primary risk record: fingerprints, payment_created_at, payment_status, observed_latitude/longitude, is_archived_basket_reference, 3DS columns.
- `sql_table:customer_accounts` — Customer identity and home_latitude/home_longitude context for distinguishing remote shopping from observed-location fraud.
- `sql_table:stores` — Joined store location axis for geo anomaly checks.
- `sql_table:shopping_baskets` — Basket/customer/store joins and archive context.
- `sql_table:shopping_basket_items` — Basket resource lines (requested_quantity) for quantity/resource reconciliation.
- `sql_table:payment_transaction_items` — Line-level reconciliation (purchased_quantity, item_unit_price_cents) for amount anomalies.
- `sql_table:product_variants` — Catalogue price joins for amount/line checks.
- `sql_table:store_inventory` — Reserve/availability arithmetic and store/SKU resource axis.
- `sql_table:return_requests` — Return/payment/basket/customer workflow joins.
- `workspace:/proc/payments/README.md` — Archived-payment semantics, observed-coordinate meaning, and opaque fingerprint semantics.
- `workspace:/proc/customers/README.md` — Coarse customer home-area coordinate semantics used by risk fixtures.
- `workspace:/proc/stores/README.md` — Store branch coordinate semantics for payment-risk/distance checks.
