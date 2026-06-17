# bp_discount v0002

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-05-21T09:41:05+00:00`
- parent: `v0001`

## Rationale

On an OK discount the trial failed with 'answer missing required reference /docs/checkout.md'. The Executor followed the previous bp_discount rule 'Do not include /docs/checkout.md unless the denial is specifically about line eligibility' and submitted refs without /docs/checkout.md. That rule is wrong: the discount policy explicitly bridges into the checkout policy at gate 7 ('Every basket line is checkoutable under docs/checkout.md'). On OK, every basket line passed the checkoutability gate, so /docs/checkout.md is an applied policy and must be cited. The new version requires /docs/checkout.md in refs whenever the line-eligibility gate is applied (OK, and any NONE_UNSUPPORTED that reached gate 7) and keeps it out of identity-only denials that never touch the line gate. The added anti-pattern names the exact failure shape so a future Executor recognises it.

## Rollback

Create a new version from v0001 content if the new refs rule turns out to over-include /docs/checkout.md (e.g. graders begin rejecting OK discounts that cite it) — the v0001 text excluded /docs/checkout.md by default.

## Dependencies
- `workspace:/docs/discounts.md` — Contains the gate list including the explicit bridge 'Every basket line is checkoutable under docs/checkout.md', plus the percent tiers, reason-code enum, and retired-phrase/campaign-label anti-patterns this BP quotes.
- `workspace:/docs/checkout.md` — Defines the line-eligibility gate (quantity <= available_today, missing inventory row = unsupported) that the discount policy applies at gate 7. The new refs rule cites this doc as an applied policy on OK discounts; if its gate text changes, this BP's quoted requirement may become stale.
- `bin_help:discount.help.txt` — Provides the /bin/discount signature <basket_id> <percent> <reason_code> <issuer_id> and the 'Applies the requested basket discount without policy checks. Read /docs/discounts.md before use.' disclaimer that motivates the BP-side gate enforcement.
