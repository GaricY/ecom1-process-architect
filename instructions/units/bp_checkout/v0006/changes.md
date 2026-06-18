# bp_checkout v0006

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-18T23:08:58+00:00`
- parent: `v0005`
- no_semantic_change: revalidated against the new dependency hashes without text edits

## Rationale

world_refresh: PA reviewed this BP and recorded it as unchanged; orchestrator re-stamped drifted dependency hashes (/docs/security.md) so the unit re-matches the refreshed world instead of falling back stale. No content change.

## Rollback

rollback to v0005 (content identical; only dependency hashes were re-stamped)

## Dependencies
- `workspace:/docs/checkout.md` — Gate set, source order, and Store Desk Checkout Vocabulary anti-patterns; the verbatim line-eligibility quote.
- `workspace:/docs/security.md` — Identity gate applied via identity_and_auth before the stock check.
- `bin_help:checkout.help.txt` — Tool signature /bin/checkout <basket_id>.
- `sql_table:shopping_baskets` — Ownership (customer_id), basket_status, store pointer, and canonical basket shape.
- `sql_table:shopping_basket_items` — Basket line requested_quantity when queried directly.
- `sql_table:store_inventory` — available_today_quantity and missing-row checkout gates, keyed by (store_id, product_sku).
