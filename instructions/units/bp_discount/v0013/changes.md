# bp_discount v0013

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-22T08:55:04+00:00`
- parent: `v0012`

## Rationale

Owning layer: topic_evidence (bp_discount). The Executor applied the correct 12% service_recovery discount and confirmed post-state, but the grader failed it for a /proc/prod refs mismatch: the two per-line product records that supplied price_cents for the subtotal (which determined the high-subtotal percent tier) were missing from refs. Across v0011/v0012 the catalogue price records sit only in `answer_records`; `refs_must_include` named cart, store, and staff but never the catalogue price rows, so the Executor projected refs without them. This was never tried-and-reverted — it is a standing gap, not a PA regression. Fix promotes the per-line catalogue price records into `refs_must_include` whenever the subtotal/percent-cap gate was evaluated, mirroring the existing checkout.md treatment with a matching step-5 'belongs in refs' clause and an anti-pattern, plus a `refs_must_not_include` carve-out so identity-only denials reached before any subtotal don't over-cite them.

## Rollback

Create a new version from v0012 content (which lacks the catalogue-price refs_must_include bullet, step-5 'belongs in refs' clause, and the matching anti-pattern) if requiring the per-line catalogue records over-cites or regresses discount tasks.

## Dependencies
- `workspace:/docs/discounts.md` — Gate set, subtotal/percent tiers, reason-code enum, manager-store gate, and the Non-Authority Bait table — the policy whose subtotal rule makes the catalogue price records load-bearing evidence.
- `workspace:/docs/checkout.md` — Same-day availability line-eligibility gate the discount policy applies at step 7.
- `workspace:/docs/security.md` — Identity/issuer authority applied via identity_and_auth for the capability and cross-boundary gates.
- `bin_help:discount.help.txt` — Tool signature <basket_id> <percent> <reason_code> <issuer_id> and the no-policy-checks disclaimer.
- `bin_help:availability.help.txt` — Same-day availability for the per-line eligibility gate.
- `sql_table:carts` — Cart ownership, store, status, discount object, and lines used by the gate set and the subtotal computation.
- `sql_table:prod` — price_cents per line SKU summed for the subtotal; these catalogue records are now required in refs whenever the subtotal/percent gate was evaluated.
- `sql_table:locations` — Store inventory for line eligibility and the store record for the manager-store gate.
- `sql_table:employees` — The /bin/id employee's roles[] and assigned store_id for the manager-store match.
