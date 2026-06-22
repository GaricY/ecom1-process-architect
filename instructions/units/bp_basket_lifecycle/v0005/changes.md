# bp_basket_lifecycle v0005

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-30T09:37:50+00:00`
- parent: `v0004`

## Rationale

Basket family renamed /proc/baskets -> /proc/carts; /proc/baskets/README.md and /proc/payments/README.md removed so record shape/status/discount semantics and archived-payment context come from the schema (carts/cart_lines, payment_ledger.archived); new 'abandoned' status added to the enum; /bin/sql down -> list/read carts via /bin/jq|cat.

## Rollback

Restore v0004 content (/proc/baskets paths, /proc/baskets/README.md + /proc/payments/README.md dependencies, shopping_baskets/shopping_basket_items SQL tables, no abandoned status).

## Dependencies
- `bin_help:jq.help.txt` — JSON read tool for cart lookups now that /bin/sql is unavailable.
- `bin_help:cat.help.txt` — Raw record read tool for cart JSON.
- `sql_table:carts` — Basket id, status, store pointer, created_at, discount object.
- `sql_table:cart_lines` — Basket line shape (sku, quantity).
- `sql_table:payment_ledger` — archived flag and cold-storage semantics where a payment outlives its cart (replaces the removed /proc/payments/README.md).
