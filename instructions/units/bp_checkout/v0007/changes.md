# bp_checkout v0007

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-22T00:02:07+00:00`
- parent: `v0006`

## Rationale

checkout.md rewritten: added the basket item-edit workflow (sanctioned direct cart-JSON edit: +1 quantity or append {sku,quantity:1}, no availability required) and changed checkout to compute same-day availability as max(on_hand-reserved,0) via /bin/availability over /proc/locations. Both are customer-only; employee identity is unsupported (employees.md). The 'Store Desk Checkout Vocabulary' slang table was removed from the doc and dropped here. SQL/store_inventory replaced by /proc reads.

## Rollback

Restore bp_checkout v0006 content with its SQL store_inventory gates and the slang anti-pattern table.

## Dependencies
- `workspace:/docs/checkout.md` — Item-edit rules, checkout gate set, the same-day availability formula, and customer-only scope.
- `workspace:/docs/security.md` — Identity/ownership gate applied via identity_and_auth.
- `bin_help:checkout.help.txt` — /bin/checkout tool signature.
- `bin_help:availability.help.txt` — Same-day availability used for the per-line checkout gate.
- `sql_table:carts` — Ownership, status, store pointer, and lines.
- `sql_table:locations` — Store inventory (on_hand/reserved) for the availability gate.
- `sql_table:catalog` — SKU resolution for item edits.
