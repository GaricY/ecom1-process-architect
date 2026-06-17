# bp_fraud_risk_review v0005

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-28T18:31:45+00:00`
- parent: `v0004`

## Rationale

Schema rename. Rewrote the two canonical SQL query shapes (observed-travel, stationary-burst) and the burst-window anti-pattern to current columns: created_at->payment_created_at, observed_lat/observed_lon->observed_latitude/observed_longitude, basket_archived->is_archived_basket_reference, path->record_path, id->payment_id, from payments->from payment_transactions. Updated the in-scope table list, the General Risk Primitives example tables (store_inventory, shopping_basket_items, return_requests), and the dependency list. Unchanged identifier columns (payment_method_fingerprint, device_fingerprint, three_ds_status/attempts/max_attempts, customer_id, store_id) were preserved verbatim.

## Rollback

Restore bp_fraud_risk_review v0004 (old payments/inventory/etc. table+column names in the SQL shapes) if the rename mapping proves wrong.

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
