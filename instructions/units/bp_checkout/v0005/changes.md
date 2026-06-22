# bp_checkout v0005

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-30T09:37:50+00:00`
- parent: `v0004`

## Rationale

checkout.md was rewritten: checkout is now customer-only and the doc adds a customer-only basket item-edit mutation (edit the cart JSON directly to add a unit), so this BP is expanded to 'Baskets and Checkout'; same-day availability is computed via /bin/availability (or /proc/locations inventory) as max(on_hand-reserved,0) since /bin/sql is down and store_inventory is gone; basket family /proc/baskets -> /proc/carts; adds do not require availability.

## Rollback

Restore v0004 content (checkout-only, employee-or-customer actor, SQL store_inventory availability gate, /proc/baskets, no item-edit section).

## Dependencies
- `workspace:/docs/checkout.md` — The basket-item-edit gate set, the checkout gate set, the same-day availability formula, and the store-floor caveats.
- `workspace:/docs/security.md` — Identity/ownership gate applied via identity_and_auth.
- `bin_help:checkout.help.txt` — Checkout tool signature <basket_id>.
- `bin_help:availability.help.txt` — Same-day availability per SKU at a store record path for the checkout line gate.
- `sql_table:carts` — Ownership, status, store pointer, and lines shape.
- `sql_table:cart_lines` — Basket line sku/quantity.
- `sql_table:location_inventory` — on_hand/reserved for the same-day availability gate.
- `sql_table:catalog` — SKU resolution for the basket item-edit path.
