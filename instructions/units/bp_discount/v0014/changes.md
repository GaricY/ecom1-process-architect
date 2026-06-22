# bp_discount v0014

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-22T11:09:43+00:00`
- parent: `v0013`

## Rationale

Owning layer: topic_evidence (bp_discount). Failure was purely a missing required ref: the Executor correctly denied a directly-named 12% price_match discount on an authorized discount_manager basket (high-tier subtotal, percent over cap -> OUTCOME_NONE_UNSUPPORTED) but omitted /docs/checkout.md from refs and scored 0.0%. /docs/checkout.md is a named member of the discount gate set ('Every basket line is checkoutable under /docs/checkout.md'); because the basket was named directly (no target selection) and the percent gate denied before the step-7 line check, the Executor concluded checkout.md 'was not applied' and dropped it. The conflicting v0013 fixed an orthogonal gap (per-line catalogue price records missing from refs) but left the checkout.md trigger at v0012's evaluation-order-dependent wording, so it does not address this failure -- hence extended, not subsumed: I keep all of v0013's catalogue-records rules verbatim (step-5 clause, refs_must_include/refs_must_not_include bullets, anti-pattern, catalog dependency note) and only widen the five checkout.md clauses (step 7, policy_docs_applied, refs_must_include, refs_must_not_include, anti-pattern) to require /docs/checkout.md on every authorized-actor decision (OUTCOME_OK / OUTCOME_NONE_UNSUPPORTED) regardless of which gate denied, excluding it only on the identity-stop OUTCOME_DENIED_SECURITY. This is a monotonic widening of the v0009->v0010 checkout.md trigger (not a reverted rule re-added) and aligns bp_discount with the shared bp_refs 'Required gate evidence' invariant and the already-shipped sibling bp_payments_3ds_recovery, which both keep a named gate input/prerequisite in refs across authorized-actor outcomes and drop it only on the identity stop.

## Rollback

Create a new version from v0013 content (restoring the 'when the line-eligibility gate was applied' / 'when checkout/line rules were applied' wording in step 7, policy_docs_applied, and refs_must_include, plus the 'identity-only denials where line rules were never applied' exclusion) if requiring /docs/checkout.md on every authorized-actor discount decision proves to over-cite it; this leaves v0013's catalogue-records rules intact.

## Dependencies
- `workspace:/docs/discounts.md` — Defines the discount gate set including the 'Every basket line is checkoutable under /docs/checkout.md' bridge, the subtotal/percent tiers that make the catalogue price records load-bearing, and the security-vs-non-security outcome split that decides when /docs/checkout.md is a required ref.
- `workspace:/docs/checkout.md` — The line-eligibility gate doc that is the cited policy; it is the named gate member whose required/forbidden ref placement this version governs.
- `workspace:/docs/security.md` — Defines the identity/issuer/authority boundary; OUTCOME_DENIED_SECURITY is the only branch where /docs/checkout.md and the catalogue price records are excluded from refs.
- `bin_help:discount.help.txt` — Tool signature /bin/discount <basket_id> <percent> <reason_code> <issuer_id> and the 'no policy checks' disclaimer quoted in the Process/Inputs.
- `bin_help:availability.help.txt` — Same-day availability max(on_hand - reserved, 0) used by the step-7 per-line checkout-eligibility check.
- `sql_table:carts` — Cart store_id, status, existing discount object, and lines read by the gate set and summed for the subtotal.
- `sql_table:catalog` — price_cents per line SKU summed for the subtotal/percent-tier gate; these catalogue records are required in refs whenever the subtotal was computed.
- `sql_table:staff` — The /bin/id employee's roles[] (discount_manager capability) and assigned store_id for the manager-store gate.
- `sql_table:stores` — Store inventory (on_hand/reserved) for the step-7 line-eligibility check and the store record for the manager-store gate.
