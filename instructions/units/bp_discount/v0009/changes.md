# bp_discount v0009

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-28T18:31:45+00:00`
- parent: `v0008`

## Rationale

Schema rename. Updated the subtotal/line-eligibility SQL the BP issues (basket_lines.quantity x products.price_cents -> shopping_basket_items.requested_quantity x product_variants.price_cents; inventory.available_today -> store_inventory.available_today_quantity) and the store cite column stores.path -> stores.record_path. Added a schema note mapping the unchanged /docs/discounts.md and /docs/checkout.md conceptual fields to current SQL columns. All verbatim policy quotes (percent tiers, reason-code enum, retired phrases, campaign labels) and the manager-store-match refs rule were preserved; dependency table names renamed.

## Rollback

Restore bp_discount v0008 content and old sql_table dependencies (baskets, basket_lines, products, inventory, employees) if the rename mapping proves wrong.

## Dependencies
- `workspace:/docs/discounts.md` — Full gate set: percent tiers, reason-code enum, retired-phrase and campaign-label anti-patterns, the line-eligibility bridge into /docs/checkout.md, and the manager-store-match gate.
- `workspace:/docs/checkout.md` — Line-eligibility gate text (quantity <= available_today, missing inventory row = unsupported) the discount policy applies at gate 8.
- `bin_help:discount.help.txt` — Tool signature /bin/discount <basket_id> <percent> <reason_code> <issuer_id> and the 'no policy checks' disclaimer.
- `sql_table:shopping_baskets` — Basket ownership, store, basket_status, discount columns, and line shape used by the gate set.
- `sql_table:shopping_basket_items` — requested_quantity used for subtotal and checkoutability checks when the line projection is queried directly.
- `sql_table:product_variants` — price_cents and canonical catalogue record_path used for subtotal and evidence.
- `sql_table:store_inventory` — available_today_quantity line-eligibility gate.
- `sql_table:stores` — Store record_path and manager-store scope evidence.
- `sql_table:employee_accounts` — Actor/store/role context (store_id) when employee records are consulted for the manager-store match.
