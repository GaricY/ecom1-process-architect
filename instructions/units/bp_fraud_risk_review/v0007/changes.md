# bp_fraud_risk_review v0007

- mode: `manual_refactor`
- created_by: `human`
- created_at: `2026-06-18T00:26:47+00:00`
- parent: `v0006`

## Rationale

Refactor refs from a flat scratchpad list into typed Evidence ledger roles. refs.md owns the shared model and safety projection; topic BPs classify their domain evidence; submission_terminal checks the completed ledger before submit.

## Rollback

Retire this version to fall back to v0006, or issue a new manual_refactor version with adjusted ledger wording.

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
