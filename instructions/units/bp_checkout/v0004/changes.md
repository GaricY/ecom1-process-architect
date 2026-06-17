# bp_checkout v0004

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-28T18:31:45+00:00`
- parent: `v0003`

## Rationale

Schema rename. The checkout stock gate reads SQL inventory: inventory->store_inventory, available_today->available_today_quantity, sku->product_sku, basket line quantity->requested_quantity. Verbatim /docs/checkout.md gate quotes (which still say 'quantity'/'available_today' because the doc was not renamed) were preserved, with a schema note mapping the doc's conceptual fields to current SQL columns. Dependency table names renamed.

## Rollback

Restore bp_checkout v0003 content and old sql_table dependencies (baskets, basket_lines, inventory) if the rename mapping proves wrong.

## Dependencies
- `workspace:/docs/checkout.md` — Gate set, source order, and Store Desk Checkout Vocabulary anti-patterns; the verbatim line-eligibility quote.
- `workspace:/docs/security.md` — Identity gate applied via identity_and_auth before the stock check.
- `bin_help:checkout.help.txt` — Tool signature /bin/checkout <basket_id>.
- `sql_table:shopping_baskets` — Ownership (customer_id), basket_status, store pointer, and canonical basket shape.
- `sql_table:shopping_basket_items` — Basket line requested_quantity when queried directly.
- `sql_table:store_inventory` — available_today_quantity and missing-row checkout gates, keyed by (store_id, product_sku).
