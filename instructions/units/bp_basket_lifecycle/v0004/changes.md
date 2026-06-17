# bp_basket_lifecycle v0004

- mode: `world_refresh`
- created_by: `codex`
- created_at: `2026-05-29T11:30:59+00:00`
- parent: `v0003`

## Rationale

Add a short archived-payment exception: missing basket files linked from archived payments are not automatically inconsistent because the payment snapshot may survive.

## Rollback

Revert to v0003 if archived-payment wording causes live basket lookups to skip ordinary missing-basket unsupported outcomes.

## Dependencies
- `workspace:/proc/baskets/README.md` — Record shape, status semantics, discount object semantics, and the 'no availability flag' rule.
- `sql_table:shopping_baskets` — Basket id, basket_status, store pointer, basket_created_at, and discount columns read by this registry.
- `sql_table:shopping_basket_items` — Basket line shape (line_number, product_sku, requested_quantity) used in reconciliation.
- `workspace:/proc/payments/README.md` — Archived-payment semantics: older payments can carry line snapshots after basket files age out.
