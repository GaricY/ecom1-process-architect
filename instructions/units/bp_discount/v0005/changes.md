# bp_discount v0005

- mode: `refresh`
- created_by: `codex`
- created_at: `2026-05-26T08:22:43+00:00`
- parent: `v0004`

## Rationale

Add an explicit policy_update_scan handoff for discount addenda while keeping discount-specific role, issuer, subtotal, reason, store, checkout-line, and refs rules local to this BP.

## Rollback

Create a new version from v0004 if delegating addendum matching to policy_update_scan causes missed discount addenda.

## Dependencies
- `workspace:/docs/discounts.md` — Full discount gate set, percent tiers, reason-code enum, store-match gate, and anti-patterns.
- `workspace:/docs/checkout.md` — Line-eligibility gate applied by the discount policy.
- `bin_help:discount.help.txt` — Tool signature and no-policy-checks disclaimer.
