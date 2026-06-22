# bp_basket_lifecycle v0006

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-22T00:02:07+00:00`
- parent: `v0005`

## Rationale

Basket family renamed /proc/baskets -> /proc/carts and SQL removed; the /proc/baskets/README + /proc/payments/README that supplied record-shape and archived-payment semantics were removed. Re-derived the cart record shape from the reconstructed projection and lifecycle/'latest active basket' semantics from /docs/checkout.md; archived-payment context now reads payment-ledger.archived.

## Rollback

Restore bp_basket_lifecycle v0005 content with its shopping_baskets SQL and /proc/*/README dependencies.

## Dependencies
- `workspace:/docs/checkout.md` — Cart status semantics and the 'latest active basket' rule.
- `sql_table:carts` — Cart id/status/store_id/created_at/lines/discount shape read by this registry.
- `sql_table:payment-ledger` — archived flag and payment line snapshot for the cold-storage cart case.
