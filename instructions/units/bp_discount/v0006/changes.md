# bp_discount v0006

- mode: `refresh`
- created_by: `codex`
- created_at: `2026-05-26T08:53:50+00:00`
- parent: `v0005`

## Rationale

Remove duplicated dated-update scan mechanics from the discount BP. It now passes discount-specific context to policy_update_scan and keeps only discount gates and interpretation of matched addenda local.

## Rollback

Create a new version from v0005 if moving scan mechanics into policy_update_scan causes missed discount addenda.

## Dependencies
- `workspace:/docs/discounts.md` — Full discount gate set, percent tiers, reason-code enum, store-match gate, and anti-patterns.
- `workspace:/docs/checkout.md` — Line-eligibility gate applied by the discount policy.
- `bin_help:discount.help.txt` — Tool signature and no-policy-checks disclaimer.
