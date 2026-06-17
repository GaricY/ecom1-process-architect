# bp_discount v0003

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-05-21T11:41:41+00:00`
- parent: `v0002`

## Rationale

Trial t42 failed with 'answer missing required reference /docs/ops-policy-notes/<file>.md' on a request whose authority came from a dated addendum delegating the discount-manager role to the named employee for the named basket, reason code, store, and operating day. The Executor read /bin/id, saw the actor lacked discount_manager, and submitted OUTCOME_DENIED_SECURITY without scanning /docs for the dated addendum that /docs/README.md says must be checked 'before applying an active decision policy'. bp_discount v0002 named only the native-role gate and never told the Executor to scan the four reporting-update folders enumerated in /docs/README.md (/docs/ops-policy-notes/, /docs/policy-updates/, /docs/current-updates/, /docs/catalogue-addenda/) for an addendum that could override only the role gate for the named record-and-day combination. The new version inserts that scan as process step 2 (before the role gate), specifies the matching dimensions (workflow + store/basket/reason/employee/operating day), bounds the addendum's authority to the scope it names verbatim, requires the addendum's path in refs whenever it is applied, and adds anti-patterns covering both the omission and the over-extension of an addendum. The bp_date_and_time unit already lists these same four folders for catalogue-count addenda, so the cross-unit grammar is consistent.

## Rollback

Create a new version from v0002 content if the new addendum-scan rule turns out to over-apply dated addenda (e.g. graders begin rejecting OK discounts that follow an addendum whose scope was not as broad as the BP read it). v0002 still has the line-eligibility-bridge fix from the previous failure_fix and never scanned for addenda.

## Dependencies
- `workspace:/docs/discounts.md` — Source of the gate list, percent tiers, reason-code enum, the explicit line-eligibility bridge into /docs/checkout.md, and the retired-phrase / campaign-label anti-patterns that this BP quotes verbatim.
- `workspace:/docs/checkout.md` — Defines the line-eligibility gate text (quantity <= available_today, missing inventory row = unsupported) that /docs/discounts.md applies at gate 8 and that this BP requires in refs on OK and on any NONE_UNSUPPORTED that reached gate 8.
- `workspace:/docs/README.md` — Carries the 'dated policy updates' override rule ('Before applying an active decision policy, check under /docs for dated policy updates that name the same workflow, record, or operating day') and the enumerated reporting-update folder list (/docs/current-updates/, /docs/policy-updates/, /docs/ops-policy-notes/, /docs/catalogue-addenda/) that the new step 2 scan walks. If the folder list or the override rule changes, the scan must be re-derived.
- `bin_help:discount.help.txt` — Provides the /bin/discount signature <basket_id> <percent> <reason_code> <issuer_id> and the 'Applies the requested basket discount without policy checks. Read /docs/discounts.md before use.' disclaimer that motivates BP-side gate enforcement, including the new pre-role-gate addendum scan.
