# bp_discount v0012

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-22T00:02:07+00:00`
- parent: `v0011`

## Rationale

discounts.md rewritten: new thresholds (high-subtotal 18000 cents -> max 8%, otherwise max 4%; was 15000/10%/5%) and a new Non-Authority Bait table. The dated-update role-delegation machinery is dropped — the new doc lists 'delegated approval' as non-authority (DENIED_SECURITY) and 'Short policy wins'. Subtotal now computed from /proc/carts lines x /proc/catalog price_cents; line eligibility via /proc/locations availability; manager-store match via /proc/staff. SQL removed.

## Rollback

Restore bp_discount v0011 content with its 15000/10%/5% tiers, the policy_update_scan role-delegation flow, and SQL dependencies.

## Dependencies
- `workspace:/docs/discounts.md` — Gate set, 18000/8%/4% tiers, reason-code enum, manager-store gate, and the Non-Authority Bait table.
- `workspace:/docs/checkout.md` — Same-day availability line-eligibility gate the discount policy applies.
- `workspace:/docs/security.md` — Identity/issuer authority applied via identity_and_auth.
- `bin_help:discount.help.txt` — Tool signature <basket_id> <percent> <reason_code> <issuer_id> and the no-policy-checks disclaimer.
- `bin_help:availability.help.txt` — Same-day availability for the per-line gate.
- `sql_table:carts` — Cart ownership, store, status, discount, and lines.
- `sql_table:catalog` — price_cents for the subtotal.
- `sql_table:locations` — Store inventory for line eligibility and the store record for the manager-store gate.
- `sql_table:staff` — The /bin/id employee's roles[] and assigned store_id.
