# bp_discount v0007

- mode: `failure_fix`
- created_by: `codex`
- created_at: `2026-05-26T15:30:16+00:00`
- parent: `v0006`

## Rationale

Pass semantic discount context to policy_update_scan instead of hard-coded update folders, and require matched dated updates that shape permit/deny decisions to be cited.

## Rollback

Create a new version from v0006 if semantic live-tree update discovery over-selects or misses discount updates.

## Dependencies
- `workspace:/docs/discounts.md` — Full discount gate set, percent tiers, reason-code enum, store-match gate, and anti-patterns.
- `workspace:/docs/checkout.md` — Line-eligibility gate applied by the discount policy.
- `bin_help:discount.help.txt` — Tool signature and no-policy-checks disclaimer.
- `sql_table:baskets` — Basket ownership, store, status, discount, and line shape used by the gate set.
- `sql_table:basket_lines` — Line quantities used for subtotal and checkoutability checks when queried directly.
- `sql_table:products` — Product price and catalogue path shape subtotal and evidence.
- `sql_table:inventory` — available_today is the line-eligibility gate.
- `sql_table:stores` — Store path and manager-store scope evidence.
- `sql_table:employees` — Employee role/store context used for authorization and issuer checks.
