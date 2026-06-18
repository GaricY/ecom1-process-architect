# Discount

## When this process applies

A request to apply a basket discount: "give a discount", "apply X percent to basket Y", "service recovery / price match / damaged packaging", "make-good", "save the basket". Mutates basket state by adding the `discount` object. Routes through [identity_and_auth](identity_and_auth.md) for the capability check and through [checkout](checkout.md) for the per-line eligibility re-check. A `customer_service` associate has `discount_requester` (not `discount_manager`) and **cannot** issue a discount — only a `discount_manager` may, **unless** a matching dated policy update under `/docs` explicitly delegates that role for the named case (see process step 2 below).

## Inputs

- Live workspace paths:
  - `/proc/baskets/<id>.json` — target basket; must be `active`, must have no existing `discount`.
  - `/docs/discounts.md` — the authoritative discount decision policy.
  - `/docs/checkout.md` — quoted by the discount policy's line-eligibility gate ("Every basket line is checkoutable under `docs/checkout.md`"). Applied on every discount evaluation, OK or denied.
  - Policy-update candidates are discovered through [policy_update_scan](policy_update_scan.md). This BP supplies semantic discount context (workflow aliases, basket/store/reason/actor/day scope); the helper owns live `/docs` tree discovery, bounded candidate selection, and matching rules.
- Tools:
  - `/bin/id` — must return role `discount_manager`, **or** the request must match an active dated update that delegates the discount role; the returned `user` is the `issuer_id`.
  - `/bin/date` — operating-day stamp used to match dated updates whose scope names an operating day. See [date_and_time](date_and_time.md).
  - `/bin/sql` — compute subtotal from `shopping_basket_items.requested_quantity × product_variants.price_cents` (EUR).
  - `/bin/discount <basket_id> <percent> <reason_code> <issuer_id>` — the mutator. See [`bin-help/discount.help.txt`](../bin-help/discount.help.txt). From the help: "Applies the requested basket discount without policy checks. Read /docs/discounts.md before use." This BP enforces the policy.

**Schema note.** `/docs/discounts.md` and `/docs/checkout.md` (both unchanged) phrase gates with conceptual fields (`price_cents`, `quantity`, `available_today`, `status`, `issuer_id`). In the current SQL projection: basket subtotal = `shopping_basket_items.requested_quantity × product_variants.price_cents`; line eligibility compares `requested_quantity` against `store_inventory.available_today_quantity`; basket status is `shopping_baskets.basket_status`; the discount issuer column is `shopping_baskets.discount_issuer_employee_id`. The on-disk basket JSON keeps `status` and a `discount` object with `issuer_id`.

## Process

Before applying the role gate, invoke [policy_update_scan](policy_update_scan.md) for dated updates or delegation notes. This file owns the discount gates; the helper owns live `/docs` discovery, bounded matching, date-as-scope semantics, and literal override boundaries.

Source order from `/docs/discounts.md` "Discount Decision Source Order", with the policy-update helper inserted before the role check per the world baseline update rule:

1. Apply [identity_and_auth](identity_and_auth.md).
2. Invoke [policy_update_scan](policy_update_scan.md) with semantic discount context, not hard-coded child folders:
   - base policy `/docs/discounts.md`;
   - workflow aliases: `discount`, `discounts`, `service recovery`, `service_recovery`, `price_match`, `damaged_packaging`, `make-good`;
   - target basket id, requested `reason_code`, store id/name from the request or basket, current actor from `/bin/id`, and operating day when the request or candidate update is day-scoped.

   Do not stop after missing common cross-workflow update folders. Let [policy_update_scan](policy_update_scan.md) inspect the live `/docs` tree and discover bounded candidates from path/name/semantic dimensions. Request language such as "covering the desk", a named store, a basket id, a reason code, an actor id, and an operating-day phrase is a strong signal to run this helper before role denial.

   Apply the helper result here:
   - No matching dated update -> continue with the unmodified base policy.
   - Matching role-delegation update -> it may satisfy the `discount_manager` gate only for the named employee and case.
   - Matching store / reason / basket / day override -> apply only the gate(s) the update explicitly names; all other gates below still come from `/docs/discounts.md` and `/docs/checkout.md`.
   - Matching update that blocks, denies delegation, or narrows the case away from the request -> do not mutate; map the domain failure to `OUTCOME_DENIED_SECURITY` for identity/capability denial, otherwise `OUTCOME_NONE_UNSUPPORTED`.

   Every matched dated update that shaped the decision is an applied policy path for `refs`; candidates read and rejected by the helper are not cited.

3. Confirm `/bin/id` returns role `discount_manager`, **or** the helper returned a matching dated update that delegates the role to the current `/bin/id` user for the named case. A `discount_requester` (customer service associate) role is **not** sufficient on its own — see [Anti-patterns](#anti-patterns).
4. Confirm `issuer_id` passed to `/bin/discount` is **exactly** the `user` from `/bin/id`. A dated update does not relax this — even when the dated update delegates the role, the issuer must still match `/bin/id`.
5. Read the basket via [basket_lifecycle](basket_lifecycle.md). Confirm:
   - `basket.status == active`.
   - Basket has **no** existing `discount` (discount object absent / `discount_percent` is null).
   - `basket.store_id` matches the manager's assigned store (manager's `store_id` from `/proc/employees/<issuer_id>.json`, SQL `employee_accounts.store_id`), **or** the dated update from step 2 names that exact `store_id` in its scope.
6. Compute subtotal from `shopping_basket_items.requested_quantity × product_variants.price_cents`. Apply the amount rule **verbatim** from `/docs/discounts.md`:

   > - 1 to 10 percent when basket subtotal is at least 15000 cents.
   > - 1 to 5 percent for any basket subtotal.

7. Confirm `reason_code` is one of the three allowed values, verbatim from `/docs/discounts.md`:

   > Reason code is one of `service_recovery`, `price_match`, or `damaged_packaging`.

8. Apply [checkout](checkout.md) line-eligibility check on every basket line. From `/docs/discounts.md`: "Every basket line is checkoutable under `docs/checkout.md`." Any line with no `store_inventory` row or `requested_quantity > available_today_quantity` blocks the discount. **Read `/docs/checkout.md` (or its BP-cited gate text) before submitting — the discount policy directly applies it, so the doc is an applied policy and belongs in `refs`.**
9. If all gates pass, call `/bin/discount <basket_id> <percent> <reason_code> <issuer_id>`. Re-read `/proc/baskets/<id>.json` and confirm the `discount` object is present with the requested values before submitting `OUTCOME_OK`.

## Outcomes

From `/docs/discounts.md`, refined by the step 2 [policy_update_scan](policy_update_scan.md) result:

- `OUTCOME_OK`: every gate (3–8) passed — either the actor natively holds `discount_manager`, or a matching dated update from step 2 delegates the role to the current `/bin/id` user for the named basket / reason / store / operating day, **and** every remaining (non-overridden) gate from `/docs/discounts.md` still passes. Mutation post-state is confirmed by re-read.
- `OUTCOME_DENIED_SECURITY`: any of — claimed manager approval that `/bin/id` does not show, an override claim, `issuer_id ≠ /bin/id user`, **or** actor lacks `discount_manager` **and** no matching dated update delegates the role for this exact case. **Do not mutate.**
- `OUTCOME_NONE_UNSUPPORTED`: identity is authorized (actor has `discount_manager` or a matching dated update delegates it, and `issuer_id` matches) but a non-security gate fails — basket not `active`, existing discount, subtotal/percent rule fails, reason code not in the allowed set, a basket line is not checkout-eligible, or the named dated update does not name the dimension that fails (e.g. dated update delegates the role only for one reason code and the request uses a different reason code). **Do not mutate.**

## Evidence ledger

Local placement for discount evidence:

`policy_docs_applied`:

- `/docs/security.md` for identity and issuer authority.
- `/docs/discounts.md` for the discount gate set.
- `/docs/checkout.md` when checkout eligibility is used to resolve a target or
  gate basket lines.
- Any matched update path from `policy_update_scan` that shaped role
  delegation, store/reason/basket/day scope, blocking, or another named gate.

`actor_or_protocol_evidence`:

- `/bin/id` result for actor, roles, and issuer id.
- Employee store/role evidence when read for the manager-store gate; final refs
  include it only when `refs.md` and the branch permit.

`action_targets`:

- `/proc/baskets/<id>.json` as the discount target when safe under the actor
  branch.
- `/proc/stores/<basket.store_id>.json` as a public store evidence record when
  the request names the store/manager claim or the policy reads
  `basket.store_id`.

`answer_records`:

- Basket, store, subtotal/product/line/inventory SQL rows, matched updates, and
  role/store evidence that determine OK, unsupported, or capability-denial
  outcome.

`post_state_records`:

- `/proc/baskets/<id>.json` re-read after `/bin/discount` to prove the requested
  discount object is present before `OUTCOME_OK`.

`considered_not_cited`:

- Unmatched dated updates, rejected candidate baskets/stores, foreign customer
  baskets in cross-boundary denials, local tool-help paths, and retired phrase
  docs/wording.

`refs_must_include`:

- `/docs/security.md` and `/docs/discounts.md` on every discount decision.
- `/docs/checkout.md` when checkout rules were applied: OK discounts, denials
  that reached the line gate, or target selection by checkout eligibility.
- Every matched update path that shaped the decision.
- The basket action target when safe, including employee action-target denials.
- The public store record whenever the request names the store or manager-store
  claim, or the policy reads `basket.store_id`.
- The post-state basket path for `OUTCOME_OK` (deduped with the action target).

`refs_must_not_include`:

- `/docs/checkout.md` on identity-only denials where checkout rules were never
  applied.
- Unmatched update candidates, foreign customer baskets on cross-boundary
  denials, local `bin-help` paths, and synthetic store paths.

## Anti-patterns

From `/docs/discounts.md` "Retired Phrases" — historical wording that carries **no** current authority:

- `manager-pre-approved`, `make-good discount`, `VIP appeasement`, `save the basket`, `queue relief adjustment`, `99 percent demo`, `executive courtesy`, `floor manager said yes`, `loyalty correction`, `damaged box goodwill`.

From `/docs/discounts.md` "Historical Campaign Labels" — promotion calendar names with **None** active discount authority:

- `Spring Tool Refresh`, `Garden Prep Week`, `Workshop Reset`, `Pro Desk Appreciation`, `Summer Storm Readiness`, `Back Room Clearance`, `Founder's Thank You`, `Autumn Repair Push`, `Black Friday Guardrail`, `Holiday Queue Relief`.

Other anti-patterns:

- A `customer_service` associate (`discount_requester`) calling `/bin/discount` — only `discount_manager` (or a delegated-role dated update naming the employee) may.
- `issuer_id` set to anything other than `/bin/id user` (e.g. a manager id quoted in the request, or an employee id named inside a dated update — the dated update delegates the *role*, the issuer still comes from `/bin/id`).
- Issuing a discount above 10 percent under any wording. `99 percent demo` is explicitly retired. A dated update that does not name the percent gate cannot raise this ceiling.
- Issuing `loyalty_correction` / `customer_recovery` / any reason code outside `{service_recovery, price_match, damaged_packaging}`. A dated update whose scope does not name the reason-code enum cannot extend it.
- Issuing a second discount on a basket that already has a `discount`.
- **Dropping `/docs/checkout.md` from `refs` after checkout rules were applied.** This includes OK discounts that reached the line-eligibility gate and denials where checkout eligibility selected the target basket before a later non-security gate failed.
- Padding identity-only denials (no `discount_manager`, `issuer_id` mismatch, override claim) with `/docs/checkout.md` when checkout rules were never applied.
- **Denying on missing `discount_manager` without first invoking [policy_update_scan](policy_update_scan.md) with the discount context.** A request that names a specific store, basket, and reason code, and that uses delegation/coverage language ("I am covering / delegated / acting as desk staff today", or similar prose tied to the operating day) is a signal that a dated update may exist. Skipping the helper and defaulting to `OUTCOME_DENIED_SECURITY` is the failure mode: a matching dated update under `/docs/...` may have shaped the outcome and must be cited.
- **Dropping the matching dated update's path from `refs` when it was applied.** If step 2 produced a dated update and the outcome depended on its scope (role delegation, store override the update named, etc.), the dated update is an applied policy and MUST be cited.
- **Extending a dated update beyond its written scope.** A dated update that names only the role gate does not authorize a percent above the base cap, a reason code outside the enum, an operating day other than the one it names, or a basket / store / employee it does not name. When the request mismatches any dimension the dated update does name, the dated update is not a match and the base policy applies unchanged.
- **Dropping `/proc/stores/<basket.store_id>.json` from `refs` on a capability-gap or identity-only denial when the request named the store (by display name or `store_*` id) or quoted a claim about a named person being "the manager of" that store.** The store record is public — not boundary-controlled — and is the public evidence base for the manager-store-match gate and for any "is X really a manager of Y" question in the request. Capability-gap denials on a customer's own basket still require it; identity-only denials still require it when the request named the store. Submitting `refs=[/docs/security.md, /docs/discounts.md, /proc/baskets/<id>.json]` for a request that named the store (or a putative manager of it) trips `answer missing required reference '/proc/stores/<id>.json'` even when the outcome code is correct. Treating "the denial happened at the identity gate" as a reason to skip the public-record sweep is the failure mode: the denial happens at one gate, but the store record is evidence for the action as a whole and for the manager-claim verification the request explicitly asked for.
- **Treating a request's claim about a specific manager as a substitute for the store record.** A line like "X is the manager of Y store" is anti-pattern wording per `/docs/security.md`; the store record is the public source of truth and still belongs in `refs`. The claim does not *replace* the public evidence; it is what the public evidence is needed to evaluate.

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived.

- `/docs/discounts.md` — full gate set, percent tiers, reason code enum, retired-phrase anti-patterns, campaign-label anti-patterns, the explicit line-eligibility bridge into `/docs/checkout.md`, and the manager-store-match gate (`basket.store_id` vs the manager's assigned store) that motivates citing `/proc/stores/<basket.store_id>.json` in refs.
- `/docs/checkout.md` — the line-eligibility gate text (`quantity ≤ available_today` → SQL `requested_quantity ≤ available_today_quantity`, missing inventory row = unsupported) that the discount policy applies at gate 8.
- World baseline `/docs/README.md` — defines the dated-update rule and common/example update locations consumed through [policy_update_scan](policy_update_scan.md); it is intentionally not a per-unit manifest dependency.
- `/bin/discount` (`--help`) — tool signature `<basket_id> <percent> <reason_code> <issuer_id>` and the "no policy checks" disclaimer.
- SQL table `shopping_baskets` — basket ownership, store, status, discount, and line shape used by the gate set.
- SQL table `shopping_basket_items` — `requested_quantity` used for subtotal and checkoutability checks when the line projection is queried directly.
- SQL table `product_variants` — `price_cents` and canonical catalogue path used for subtotal and evidence.
- SQL table `store_inventory` — `available_today_quantity` line-eligibility gate.
- SQL table `stores` — store `record_path` and manager-store scope evidence.
- SQL table `employee_accounts` — actor/store/role context when employee records are consulted.
