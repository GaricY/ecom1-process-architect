# bp_basket_lifecycle v0003

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-28T18:31:46+00:00`
- parent: `v0002`

## Rationale

Schema rename. The SQL projection this registry reads changed: baskets->shopping_baskets, basket_lines->shopping_basket_items (line_no/sku/quantity->line_number/product_sku/requested_quantity), discount_issuer_id->discount_issuer_employee_id, and inventory->store_inventory in the re-check anti-pattern. Added a schema note distinguishing the unchanged on-disk basket JSON field names (id, status, created_at, lines[].sku/quantity, discount.issuer_id) from the renamed SQL columns, and added sql_table dependencies (previously none) so future basket/line shape changes trigger review.

## Rollback

Restore bp_basket_lifecycle v0002 content and drop the added sql_table dependencies if the rename mapping proves wrong.

## Dependencies
- `workspace:/proc/baskets/README.md` — Record shape, status semantics, discount object semantics, and the 'no availability flag' rule.
- `sql_table:shopping_baskets` — Basket id, basket_status, store pointer, basket_created_at, and discount columns read by this registry.
- `sql_table:shopping_basket_items` — Basket line shape (line_number, product_sku, requested_quantity) used in reconciliation.
