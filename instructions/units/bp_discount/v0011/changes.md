# bp_discount v0011

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-30T09:37:50+00:00`
- parent: `v0010`

## Rationale

discounts.md changed the thresholds (high-subtotal 18000 cents -> max 8 percent; any-basket max 4 percent), replacing the old 15000-cents/1-10-percent and 1-5-percent tiers; employee record family /proc/employees -> /proc/staff; subtotal/line-eligibility read from /proc/carts, /proc/catalog, /proc/locations via /bin/jq + /bin/availability since /bin/sql is down; store evidence path -> /proc/locations; the dated-update delegation logic and store-record refs rule are preserved.

## Rollback

Restore v0010 content (15000-cents/1-10-percent + 1-5-percent tiers, /proc/employees + /proc/stores, SQL subtotal over shopping_basket_items x product_variants).

## Dependencies
- `workspace:/docs/discounts.md` — Gate set, the 18000-cent/8-percent/4-percent tiers, reason-code enum, non-authority bait, the line-eligibility bridge into checkout, and the manager-store-match gate.
- `workspace:/docs/checkout.md` — The line-eligibility (same-day availability) gate the discount policy applies.
- `workspace:/docs/security.md` — Identity gate applied via identity_and_auth.
- `bin_help:discount.help.txt` — Signature <basket_id> <percent> <reason_code> <issuer_id> and the no-policy-checks disclaimer.
- `bin_help:availability.help.txt` — Same-day availability for the per-line eligibility re-check.
- `sql_table:carts` — Basket ownership, store, status, discount object.
- `sql_table:cart_lines` — quantity for subtotal and line checks.
- `sql_table:catalog` — price_cents for subtotal.
- `sql_table:location_inventory` — on_hand/reserved for line eligibility.
- `sql_table:locations` — Store record_path and manager-store scope evidence.
- `sql_table:staff` — Issuer role and assigned store_id.
