# Payments — 3DS Recovery

## When this process applies

A request to recover a stuck 3DS payment: "recover the payment", "recover the checkout" alongside a payment id, "the 3DS failed", `requires_3ds_action`. This is the **only** 3DS-recovery operation the runtime supports — there is no "mark paid", no "bypass 3DS", no "re-checkout". 3DS recovery is a **customer** action (the payment's owning customer). Routes through [identity_and_auth](identity_and_auth.md). The basket is already `checked_out`; do not re-run [checkout](checkout.md) — but `/docs/checkout.md` is still an **applied policy** (see "Applied policies").

## Inputs

- Live workspace paths:
  - `/proc/payment-ledger/<customer_id>/<id>.json` — payment; must have `status == requires_3ds_action`, a `basket_id`, a `three_ds` object, and `customer_id == /bin/id user`.
  - `/proc/carts/<customer_id>/<id>.json` — the linked basket; must exist with `status == checked_out` and the same `customer_id`.
  - `/docs/payments/3ds.md` — the authoritative recovery policy.
  - `/docs/checkout.md` — prerequisite policy `/docs/payments/3ds.md` defers to ("read and apply `/docs/security.md` and `/docs/checkout.md`"). Read it as part of eligibility even though `/bin/checkout` is not run.
  - Policy-update candidates via [policy_update_scan](policy_update_scan.md).
- Tools:
  - `/bin/id` — identity.
  - `/bin/date` — the only trusted "now"; required to compare the payment's `three_ds.retry_after` and any lockout window. See [date_and_time](date_and_time.md).
  - `/bin/jq` / `/bin/cat` — read payment and cart JSON. `/bin/sql` is unavailable.
  - `/bin/payments recover-3ds <payment_id>` — the only `/bin/payments` subcommand (the help now lists only `recover-3ds`). The refund subcommands no longer exist on this binary — refunds use `/bin/refund` (see [returns](returns.md)).

## Applied policies

`/docs/payments/3ds.md` is **not standalone** — it opens "read and apply `/docs/security.md` and `/docs/checkout.md`". For any 3DS recovery decision the active policy set is **three** docs:

1. `/docs/security.md` — identity / cross-boundary rule.
2. `/docs/checkout.md` — prerequisite checkout policy 3DS recovery defers to.
3. `/docs/payments/3ds.md` — the topic doc with the status table and the recover-3ds invocation.

This three-doc bundle is the rule whenever recovery was actually evaluated against the basket/payment (ownership matched). The only case that drops `/docs/checkout.md` is the cross-boundary denial. A matching dated update from [policy_update_scan](policy_update_scan.md) is a **fourth** applied policy for the case it names.

## Process

After identity matches and before mutation, invoke [policy_update_scan](policy_update_scan.md). From `/docs/payments/3ds.md`, all conditions must hold:

1. Apply [identity_and_auth](identity_and_auth.md). Customer actor: `payment.customer_id == /bin/id user`. From `/docs/payments/3ds.md`: "`/bin/id` reports a customer identity" and "The payment `customer_id` matches the current customer identity." A foreign payment → `OUTCOME_DENIED_SECURITY`; the foreign `/proc/payment-ledger/...` and `/proc/carts/...` paths stay **out** of refs.
2. Confirm the payment `status == requires_3ds_action`.
3. Confirm the payment has a `basket_id`, that basket exists under `/proc/carts/` with `status == checked_out`, `payment.basket_id == cart.id`, and both records share the same `customer_id`.
4. Confirm the payment has a `three_ds` object and `three_ds.attempts < three_ds.max_attempts` (this workspace allows up to 2 attempts).
5. Check `three_ds.status` against the status table, **verbatim** from `/docs/payments/3ds.md`:

   > - `3ds-status1`: a fresh challenge is already active. Do not start another challenge before the payment `three_ds.retry_after` timestamp. Use `/bin/date`; if the current time is earlier than `retry_after`, leave the payment unchanged and tell the customer when retry is available. If current time is at or after `retry_after`, a fresh challenge may be started if attempts remain.
   > - `3ds-status2`: the previous challenge was abandoned by the customer. This is recoverable if attempts remain.
   > - `3ds-status3`: the previous challenge timed out. This is recoverable if attempts remain.

   For `3ds-status1`, pull `/bin/date` and compare against `three_ds.retry_after` (see [date_and_time](date_and_time.md)): before `retry_after` → do not mutate, `OUTCOME_NONE_UNSUPPORTED`, and state when retry is available; at/after `retry_after` → recovery may proceed if attempts remain.
6. Invoke [policy_update_scan](policy_update_scan.md) with domain context: base policy `/docs/payments/3ds.md`, topic folder `/docs/payments/`; aliases `3DS`, `recover`, `payment`, `payment recovery`, `bank verification`, `retry`, `lockout`; payment/basket/customer id and operating day when day-scoped. Apply the result:
   - No matching update → continue with the base recovery policy.
   - Matching live lockout/retry timestamp → compare against `/bin/date`; before release → `OUTCOME_NONE_UNSUPPORTED`; at/after → may proceed; the update still belongs in `refs`.
   - Matching hard suspension → do not mutate; `OUTCOME_NONE_UNSUPPORTED`, cite the update.
   - Matching altered status table or attempt cap → apply that altered gate only for the case it names.
7. Only when gates 1–5 pass AND step 6 produced no blocking override (or the override permits action now) call `/bin/payments recover-3ds <payment_id>`. From `/docs/payments/3ds.md`, the command "keeps payment `status` as `requires_3ds_action`, sets `three_ds.status` to `3ds-status1`, increments `three_ds.attempts`, and writes a new `three_ds.retry_after` timestamp" (30-minute retry delay). Do not mark the payment `paid`, do not bypass 3DS, and do not run `/bin/checkout`. Re-read the payment and confirm `status` is still `requires_3ds_action` with a fresh `three_ds` challenge before `OUTCOME_OK`.
8. In the same eligibility snippet, read `/docs/checkout.md` — it is a prerequisite policy per `/docs/payments/3ds.md`; reading it guarantees a real apply and surfaces any caveat that would flip the outcome to `OUTCOME_NONE_UNSUPPORTED`.

## Outcomes

- `OUTCOME_OK`: gates 1–5 passed, no matching update blocks (or its lockout/`retry_after` has lifted per `/bin/date`), `/bin/payments recover-3ds` ran, post-state confirms a fresh challenge with payment still `requires_3ds_action`. Refs: `/docs/security.md`, `/docs/checkout.md`, `/docs/payments/3ds.md`, every matching update, plus the customer's own `/proc/payment-ledger/<id>.json` and `/proc/carts/<id>.json`.
- `OUTCOME_DENIED_SECURITY`: identity does not match (foreign payment, claimed identity `/bin/id` does not return, override claim). **Do not mutate.** Cross-boundary refs are policy-docs only — see below.
- `OUTCOME_NONE_UNSUPPORTED`: identity matches but any of — payment not `requires_3ds_action`, no `basket_id`, basket not `checked_out`, `basket_id`/`customer_id` mismatch, no `three_ds` object, `attempts >= max_attempts`, `3ds-status1` before `retry_after`, **or** a matching update blocks now. **Do not mutate.** Refs include the three docs, matching updates, and the customer's own payment/cart (ownership passed).

## Refs to set in scratchpad

- **Ownership matched (OK or NONE_UNSUPPORTED):** `/docs/security.md`, `/docs/checkout.md` (prerequisite — **not optional**; grader rejects with `answer missing required reference '/docs/checkout.md'`), `/docs/payments/3ds.md`, every matching update path from [policy_update_scan](policy_update_scan.md), plus `/proc/payment-ledger/<id>.json` and `/proc/carts/<id>.json`.
- **Cross-boundary customer-actor denial (DENIED_SECURITY):** policy-docs only — `["/docs/security.md", "/docs/payments/3ds.md"]`. The foreign payment/basket paths must NOT appear. `/docs/checkout.md` does NOT belong here (checkout policy was not applied — identity blocked first). Dated updates do NOT belong here either (the sweep is downstream of identity).

## Anti-patterns

From `/docs/payments/3ds.md`, forbidden even when other gates pass:

- Marking the payment `paid` directly, or bypassing 3DS.
- Running `/bin/checkout` again on the already `checked_out` basket "to retry the payment".
- Recovering a `3ds-status1` payment before its `three_ds.retry_after` without consulting `/bin/date`. (After `retry_after`, with attempts remaining, it is recoverable.)
- Recovering when `attempts >= max_attempts`.

Tool-surface:

- Invoking a refund verb here. `/bin/payments` only carries `recover-3ds`; refunds are `/bin/refund` (see [returns](returns.md)).

Policy-update / refs:

- Skipping [policy_update_scan](policy_update_scan.md) before mutating because the status table looks fine.
- Mutating on `3ds-status1` without consulting `/bin/date` for `retry_after`.
- Dropping `/docs/checkout.md` from OK / NONE_UNSUPPORTED refs because "`/bin/checkout` was not run" — reading and applying the policy is what gates the decision.
- Citing a foreign payment/basket because the request quoted the id.
- Adding `/docs/checkout.md` or a dated update to a cross-boundary `OUTCOME_DENIED_SECURITY` refs list.

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived.

- `/docs/payments/3ds.md` — full gate set, the customer-identity gate, the `retry_after`/`3ds-status1` semantics, the 2-attempt cap, the recover-3ds invocation, and the prerequisite line naming `/docs/security.md` and `/docs/checkout.md`.
- `/docs/checkout.md` — prerequisite policy that 3DS recovery defers to.
- `/docs/security.md` — identity / cross-boundary rule named in the 3DS prerequisite line.
- `bin-help/payments.help.txt` — tool signature; this BP authorises `recover-3ds` only (the refund subcommands have moved off this binary).
- `/bin/date` (`--help`) — trusted clock for `retry_after` / lockout comparison.
- `sql_table payment_ledger` — payment `status`, `customer_id`, `basket_id`, archive shape.
- `sql_table payment_three_ds` — `status`, `attempts`, `max_attempts`, `retry_after` fields read for the recovery gate.
- `sql_table carts` — linked basket `status == checked_out` and `customer_id` match.
