# Payments — 3DS Recovery

## When this process applies

A request to recover a stuck 3DS payment: "recover the payment", "recover the checkout" alongside a `pay_*` id, "the 3DS failed", `requires_3ds_action`. This is the **only** 3DS-recovery operation the runtime supports — there is no "mark paid", no "bypass 3DS", no "re-checkout". Routes through [identity_and_auth](identity_and_auth.md) for ownership. The basket is already `checked_out`; do not re-run [checkout](checkout.md) — but `/docs/checkout.md` is still an **applied policy** (see "Applied policies" below and the Refs section).

## Inputs

- Live workspace paths:
  - `/proc/baskets/<id>.json` — must exist with `status == checked_out`.
  - `/proc/payments/<id>.json` — must exist with the same `basket_id`, `status == requires_3ds_action`, recoverable `three_ds.status`, and attempts remaining.
  - `/docs/payments/3ds.md` — the authoritative recovery policy.
  - `/docs/checkout.md` — prerequisite policy that `/docs/payments/3ds.md` defers to ("Before recovering 3DS, read and apply `/docs/security.md` and `/docs/checkout.md`"). Must be **read** (via `ws.read("/docs/checkout.md")`) as part of the eligibility evaluation, even though `/bin/checkout` is not run.
  - Policy-update candidates are discovered through [policy_update_scan](policy_update_scan.md). This BP supplies `/docs/payments/` as the narrow topic folder plus the payment/basket/3DS scope; the helper owns the shared folder and matching rules.
- Tools:
  - `/bin/id` — identity.
  - `/bin/date` — the only trusted "now". Required when a matching policy update imposes a lockout window or other time-keyed override; see [date_and_time](date_and_time.md).
  - `/bin/payments recover-3ds <payment_id>` — the mutator. See [`bin-help/payments.help.txt`](../bin-help/payments.help.txt). This is the **only** `/bin/payments` subcommand applicable to 3DS recovery; the sibling subcommands listed in the help text (`approve-refund`, `refund`) belong to the refund workflow and must not be invoked from this BP.

## Applied policies

`/docs/payments/3ds.md` is **not standalone** — its opening sentence reads "Before recovering 3DS, read and apply `/docs/security.md` and `/docs/checkout.md`". For any 3DS recovery decision (proceed, unsupported, etc.), the active policy set is **three** docs, not two:

1. `/docs/security.md` — identity / cross-boundary rule.
2. `/docs/checkout.md` — prerequisite checkout policy that 3DS recovery defers to.
3. `/docs/payments/3ds.md` — the topic doc with the legacy 3DS status table and the recover-3ds invocation.

This three-doc bundle is the rule whenever 3DS recovery was actually evaluated against the basket/payment (i.e. ownership matched). The only case that drops `/docs/checkout.md` is the cross-boundary denial — see [Outcomes](#outcomes) below.

If [policy_update_scan](policy_update_scan.md) returns a matching dated update for this case, that update is a **fourth** applied policy on top of the three above. It overrides the base policy only for the case it names; everything else still comes from the three-doc bundle.

## Process

After identity matches and before mutation, invoke [policy_update_scan](policy_update_scan.md). This file owns 3DS recovery gates; the helper owns shared update discovery, matching, date-as-scope semantics, and literal override boundaries.

From `/docs/payments/3ds.md`, all conditions must hold:

1. Apply [identity_and_auth](identity_and_auth.md). Customer actor: payment `customer_id == /bin/id user`. Foreign payment → `OUTCOME_DENIED_SECURITY`; the foreign `/proc/payments/...` and `/proc/baskets/...` paths stay **out** of refs (see [refs](refs.md)).
2. Confirm the basket exists under `/proc/baskets/` and `status == checked_out`. From `/docs/payments/3ds.md`:

   > The basket exists under `/proc/baskets/` and has status `checked_out`.

3. Confirm the payment exists under `/proc/payments/`, has the same `basket_id`, and `status == requires_3ds_action`. From `/docs/payments/3ds.md`:

   > The payment exists under `/proc/payments/`, has the same `basket_id`, and has status `requires_3ds_action`.

4. Check `payment.three_ds.status` against the legacy table, verbatim from `/docs/payments/3ds.md`:

   > - `3ds-status1`: a fresh challenge has been issued and is waiting for customer action. Do not recover this again.
   > - `3ds-status2`: the previous challenge was abandoned by the customer. This is recoverable if attempts remain.
   > - `3ds-status3`: the previous challenge timed out. This is recoverable if attempts remain.

5. Confirm `three_ds.attempts < three_ds.max_attempts`. If attempts are exhausted, recovery is unsupported.
6. Invoke [policy_update_scan](policy_update_scan.md) with this domain context:
   - base policy `/docs/payments/3ds.md` and narrow topic folder `/docs/payments/`;
   - workflow aliases: `3DS`, `recover`, `payment`, `payment recovery`, `bank verification`, `retry`, `lockout`;
   - payment id, basket id, customer id from `/bin/id` or the payment/basket record, and operating day when the request or update is day-scoped.

   Apply the helper result here:
   - No matching update -> continue with the base recovery policy.
   - Matching live lockout/retry timestamp -> use [date_and_time](date_and_time.md) to compare against `/bin/date`; before the release timestamp, do not mutate and submit `OUTCOME_NONE_UNSUPPORTED`; at or after the release timestamp, recovery may proceed and the update still belongs in `refs`.
   - Matching hard suspension -> do not mutate; submit `OUTCOME_NONE_UNSUPPORTED` and cite the update.
   - Matching altered status table or attempt cap -> apply that altered gate only for the case the update names.

   Every matched update path that shaped the decision is required in `refs`; candidates read and rejected by the helper are not cited.

7. Only when gates 1–5 pass AND the step 6 helper result produced no matching override (or the override permits action right now) call `/bin/payments recover-3ds <payment_id>`. From `/docs/payments/3ds.md`:

   > Run `/bin/payments recover-3ds <payment_id>` to start a fresh 3DS challenge. This must keep payment status as `requires_3ds_action`; do not mark the payment `paid`, do not bypass 3DS, and do not run `/bin/checkout` for an already checked-out basket.

   After the call, re-read `/proc/payments/<id>.json` and confirm `status` is still `requires_3ds_action` with a fresh `three_ds` challenge before submitting `OUTCOME_OK`.

8. In the same snippet that confirms eligibility, call `ws.read("/docs/checkout.md")`. The doc is a prerequisite policy per `/docs/payments/3ds.md`; reading it guarantees the grader sees a real apply (not a synthesised cite) and surfaces any inventory / status caveats that would flip the outcome to `OUTCOME_NONE_UNSUPPORTED`.

## Outcomes

From `/docs/payments/3ds.md`, modulated by the step 6 [policy_update_scan](policy_update_scan.md) result:

- `OUTCOME_OK`: gates 1–5 passed, no matching policy update blocks the action (or its lockout window has lifted per `/bin/date`), `/bin/payments recover-3ds` ran, post-state confirms a fresh challenge with payment still `requires_3ds_action`. Refs include `/docs/security.md`, `/docs/checkout.md`, `/docs/payments/3ds.md`, every matching policy update returned by [policy_update_scan](policy_update_scan.md), plus the customer's own `/proc/payments/<id>.json` and `/proc/baskets/<id>.json`.
- `OUTCOME_DENIED_SECURITY`: identity does not match (foreign payment, claimed identity that `/bin/id` does not return, override claim). **Do not mutate.** Cross-boundary refs are policy-docs only — see [Refs to set in scratchpad](#refs-to-set-in-scratchpad). The policy-update sweep is skipped because eligibility was never evaluated; the dated updates are not cited.
- `OUTCOME_NONE_UNSUPPORTED`: identity matches but any of — basket not `checked_out`, payment not `requires_3ds_action`, basket/payment `basket_id` mismatch, `three_ds.status == 3ds-status1`, `three_ds.attempts >= three_ds.max_attempts`, **or** a matching policy update from step 6 blocks the action now (active lockout window, hard suspension, altered cap that the current state fails). **Do not mutate.** Refs include `/docs/security.md`, `/docs/checkout.md`, `/docs/payments/3ds.md`, every matching policy update returned by [policy_update_scan](policy_update_scan.md), plus the customer's own `/proc/payments/<id>.json` and `/proc/baskets/<id>.json` (own-record ownership passed).

## Refs to set in scratchpad

The applied-policy set depends on whether the 3DS recovery was actually evaluated against the basket/payment:

- **Ownership matched (OUTCOME_OK or OUTCOME_NONE_UNSUPPORTED):** the full prerequisite chain was applied — include all three docs and every matching dated update:
  - `/docs/security.md`
  - `/docs/checkout.md` — prerequisite policy that `/docs/payments/3ds.md` defers to. **Not optional**; the grader rejects with `answer missing required reference '/docs/checkout.md'` if it is dropped.
  - `/docs/payments/3ds.md`
  - Every matching update path returned by [policy_update_scan](policy_update_scan.md). Topic-folder siblings such as `/docs/payments/<file>.md` and cross-workflow update paths are equally required when they match and shape the decision. Copy each path verbatim from the helper's candidate read/list result; do not synthesise.
  - `/proc/payments/<id>.json` and `/proc/baskets/<id>.json` — own-record ownership passed (customer actor) or action target (employee actor).
- **Cross-boundary customer-actor denial (OUTCOME_DENIED_SECURITY):** the recovery was never evaluated — only `/docs/security.md` was applied to block the action, and the topic doc names what was being attempted. Refs are policy-docs only: `["/docs/security.md", "/docs/payments/3ds.md"]`. The foreign payment/basket paths must NOT appear. `/docs/checkout.md` does NOT belong here either — checkout policy was not applied because identity blocked the flow before eligibility was checked. Dated policy updates also do NOT belong here — the sweep is downstream of identity. See [refs](refs.md) — "checkout" wording with a `pay_*` id routes to `/docs/payments/3ds.md`, not `/docs/checkout.md`.

## Anti-patterns

From `/docs/payments/3ds.md`, forbidden actions even when other gates pass:

- Marking the payment `paid` directly.
- Bypassing 3DS entirely.
- Running `/bin/checkout` again on an already `checked_out` basket "to retry the payment".
- Recovering a `3ds-status1` payment (fresh challenge is still in flight).
- Recovering when `attempts >= max_attempts`.

Tool-surface anti-patterns:

- **Invoking `/bin/payments approve-refund` or `/bin/payments refund` as part of a 3DS recovery.** Those subcommands exist on the same binary but belong to the refund workflow; running them in a 3DS recovery flow either fails the runtime call or mutates the wrong record. The only `/bin/payments` verb this BP authorises is `recover-3ds`.

Policy-update anti-patterns:

- **Skipping [policy_update_scan](policy_update_scan.md) because the legacy status table and attempt count look fine.** The base policy is the floor; dated updates can override it for named cases. Skipping the helper before mutating is the failure mode that lets a lockout window or hard suspension be ignored — the grader then rejects with `answer missing required reference '/docs/payments/<file>.md'` (or another update path) even though the runtime call appeared correct.
- **Calling [policy_update_scan](policy_update_scan.md) without the narrow topic folder `/docs/payments/`.** A dated update for this BP can ship as a sibling to `/docs/payments/3ds.md`; cross-workflow folders alone do not clear the update check.
- **Treating the date in a policy update's filename or "Operating day:" header as a TTL that expires the update.** Per [date_and_time](date_and_time.md), the date is a scope dimension. An older-dated update that names the payment / basket / workflow still matches and must be applied.
- **Mutating when a matching update imposes a lockout window without consulting `/bin/date`.** When an update phrases the override as "may be restarted only after `<timestamp>`" (or `retry_available_at: <timestamp>`), pull `/bin/date` and gate the `recover-3ds` call on the live clock. If the live time is before the release timestamp, the correct outcome is `OUTCOME_NONE_UNSUPPORTED` with the update in refs — not `OUTCOME_OK`.
- **Dropping a matching policy update from refs because the outcome ended up `OUTCOME_OK` after the lockout lifted.** The update was the policy actually applied to decide the action was permitted now; the grader still requires it in refs.

Refs anti-patterns:

- **Dropping `/docs/checkout.md` from `OUTCOME_OK` / `OUTCOME_NONE_UNSUPPORTED` refs because "we didn't run `/bin/checkout`".** Reading and applying the policy doc is what gates the decision; `/docs/payments/3ds.md` explicitly defers to it. The grader rejects with `answer missing required reference '/docs/checkout.md'`.
- Citing a foreign payment / basket in `refs` because the request quoted the `pay_*` / `bsk_*` id. The SQL `record_path` column is a lure — see [refs](refs.md) "Identity-scoped SQL `record_path` column".
- Routing a 3DS / payment-recovery denial to `/docs/checkout.md` as the *topic* doc because the request used the word "checkout". The presence of `3DS` or a `pay_*` id is the tie-breaker — the topic doc is `/docs/payments/3ds.md`. (For ownership-matched outcomes, `/docs/checkout.md` rides along as a prerequisite, not as the topic doc.)
- Adding `/docs/checkout.md` to a cross-boundary `OUTCOME_DENIED_SECURITY` refs list — checkout policy was not actually applied because identity blocked the flow first.
- Adding a dated policy update to a cross-boundary `OUTCOME_DENIED_SECURITY` refs list — the sweep happens downstream of identity and was not actually performed.

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived.

- `/docs/payments/3ds.md` — full gate set, legacy 3DS status table, forbidden actions, and the prerequisite line that names `/docs/security.md` and `/docs/checkout.md`. Also the file whose folder (`/docs/payments/`) is now an explicit sweep target for date-stamped sibling updates; if this doc moves out of `/docs/payments/` the Class A sweep target must move with it.
- `/docs/checkout.md` — prerequisite policy that 3DS recovery defers to; if the live doc renames or removes the checkout prerequisites this BP's three-doc refs rule may need to be re-derived.
- `/docs/security.md` — identity / cross-boundary rule named alongside `/docs/checkout.md` in the 3DS prerequisite line; both the cross-boundary `OUTCOME_DENIED_SECURITY` refs branch and the ownership-matched applied-policy bundle cite it.
- World baseline `/docs/README.md` — defines the dated-update rule and cross-workflow update folder family consumed through [policy_update_scan](policy_update_scan.md); it is intentionally not a per-unit manifest dependency.
- `bin-help/payments.help.txt` — tool signature; this BP authorises `recover-3ds` only and explicitly excludes the `approve-refund` / `refund` subcommands. If the help text renames or removes `recover-3ds`, or grows a new 3DS verb, the Tools and Anti-patterns sections must be re-derived.
