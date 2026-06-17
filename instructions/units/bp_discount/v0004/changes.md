# bp_discount v0004

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-05-22T03:15:47+00:00`
- parent: `v0003`

## Rationale

Trial t28 failed with 'answer missing required reference /proc/stores/store_graz_lend.json' on a customer-actor capability-gap denial. The request named the store by display name ('PowerTool Graz Lend') and quoted a claim that a specific person was its manager. The executor correctly identified the case as own-record (basket.customer_id == /bin/id user) and kept the basket in refs, but dropped the public store record. bp_refs_and_submission v0005 already requires the public-record sweep in every actor/ownership branch, but the executor anchored on bp_discount v0003's local 'Refs to set in scratchpad' enumeration (security.md / discounts.md / checkout.md / addendum / basket) which never lists /proc/stores/<basket.store_id>.json. Fix: add the store-record bullet to that enumeration so the executor cannot drop it when reading the discount unit's checklist, add a matching anti-pattern, and extend the /docs/discounts.md dependency rationale to mention the manager-store-match gate that motivates citing the store. The rule is generalisable: it fires whenever the request names a store (by display name or store_* id) or whenever the discount policy reads basket.store_id, across customer cross-boundary, customer own-record, employee, and guest cases, on both OK and denial paths.

## Rollback

Create a new version from v0003 content if the added store-record rule over-includes /proc/stores/<id>.json on discount denials whose request did not actually lean on the store (e.g. graders begin flagging extra store refs on denials that hit gate 6 / gate 7 without any store-named or manager-named claim).

## Dependencies
- `workspace:/docs/discounts.md` — Source of the gate list, percent tiers, reason-code enum, the line-eligibility bridge into /docs/checkout.md, the manager-store-match gate (basket.store_id vs manager's assigned store) that motivates citing /proc/stores/<basket.store_id>.json on every authorised OK and on denials where the store gate or store-named request is in play, and the retired-phrase / campaign-label anti-patterns this BP quotes verbatim.
- `workspace:/docs/checkout.md` — Defines the line-eligibility gate text (quantity <= available_today, missing inventory row = unsupported) that /docs/discounts.md applies at gate 8 and that this BP requires in refs on OK and on any NONE_UNSUPPORTED that reached gate 8.
- `bin_help:discount.help.txt` — Provides the /bin/discount signature <basket_id> <percent> <reason_code> <issuer_id> and the 'Applies the requested basket discount without policy checks. Read /docs/discounts.md before use.' disclaimer that motivates BP-side gate enforcement, including the pre-role-gate addendum scan and the public-record sweep this version adds.
