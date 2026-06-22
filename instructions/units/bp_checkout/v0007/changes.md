# bp_checkout v0007

- mode: `refresh`
- created_by: `process_architect`
- created_at: `2026-05-30T18:11:11+00:00`
- parent: `v0006`

## Rationale

Proc-family rename in the workspace: /docs/checkout.md now declares 'Basket records live under /proc/baskets' (was /proc/carts), and the world AGENTS.MD renamed /proc/locations -> /proc/stores alongside the basket move. The BP's Inputs, Process step A.4, and Refs section all pin concrete /proc paths, so the prose names paths that no longer resolve. Edit is a pure path rewrite: /proc/carts/<customer_id>/<id>.json -> /proc/baskets/<customer_id>/<id>.json, /proc/locations/<city>/<store_id>.json -> /proc/stores/<city>/<store_id>.json. All gates, outcomes, anti-patterns, and the v0006 dependency contract (workspace docs + command bin-helps, no sql_table) are preserved.

## Rollback

Revert to v0006 (bp_admin rollback bp_checkout --from v0006, or retire the new version) to restore the /proc/carts and /proc/locations path strings if the proc-family rename is itself rolled back.

## Dependencies
- `workspace:/docs/checkout.md` — Basket-item-edit gate set, checkout gate set, same-day-availability formula, 'adds do not require availability' rule, store-floor caveats, and the basket-records-location sentence that triggered this refresh.
- `workspace:/docs/security.md` — Identity/ownership gate applied via identity_and_auth before any basket mutation.
- `bin_help:checkout.help.txt` — Checkout tool signature <basket_id>; signature change would invalidate Process step B.3.
- `bin_help:availability.help.txt` — Same-day availability per SKU at a store record path; argument shape backs Process step B.2.
