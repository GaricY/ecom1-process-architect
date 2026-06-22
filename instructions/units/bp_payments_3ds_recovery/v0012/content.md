# Payments — 3DS Recovery

## When this process applies

A request to recover a stuck 3DS payment: "recover the payment", "recover the checkout" alongside a `pay_*` id, "the 3DS failed", `requires_3ds_action`. This is the **only** 3DS-recovery operation the runtime supports — there is no "mark paid", no "bypass 3DS", no "re-checkout". This is a customer-only action; an employee identity is `OUTCOME_NONE_UNSUPPORTED` (`/docs/employees.md`). The basket is already `checked_out`; do not re-run [checkout](checkout.md), but `/docs/checkout.md` is still an applied prerequisite policy.

## Inputs

- Live workspace paths:
  - `/proc/payment-ledger/<id>.json` — payment; must have `status == requires_3ds_action`, matching `customer_id`, a `basket_id`, a `three_ds` object, and attempts remaining.
  - `/proc/carts/<id>.json` — linked basket; must exist with `status == checked_out` and the same `customer_id`.
  - `/docs/payments/3ds.md` — the authoritative recovery policy.
  - `/docs/security.md` and `/docs/checkout.md` — prerequisites named by `/docs/payments/3ds.md` ("read and apply `/docs/security.md` and `/docs/checkout.md`").
- Tools: `/bin/id` (identity); `/bin/date` (the only trusted "now", required by the `3ds-status1` retry window); `/bin/payments recover-3ds <payment_id>` the mutator (`bin-help/payments.help.txt`). `recover-3ds` is the only `/bin/payments` subcommand. SQL is unavailable — read `/proc` JSON directly.

## Process

A 3DS recovery is allowed only when **all** are true (`/docs/payments/3ds.md`):

> - `/bin/id` reports a customer identity.
> - The payment `customer_id` matches the current customer identity.
> - The payment `status` is `requires_3ds_action`.
> - The payment has a `basket_id`, and that basket exists with status `checked_out`.
> - The payment `basket_id` matches the basket `id`, and both records have the same `customer_id`.
> - The payment has a `three_ds` object.
> - `three_ds.attempts` is less than `three_ds.max_attempts`.
> - The current 3DS status is recoverable under the status table below.

1. Apply [identity_and_auth](identity_and_auth.md). Customer actor: payment `customer_id == /bin/id` `user`. Foreign payment → `OUTCOME_DENIED_SECURITY`; the foreign payment/cart paths stay out of refs. Employee identity → `OUTCOME_NONE_UNSUPPORTED` (`/docs/employees.md`).
2. Confirm payment `status == requires_3ds_action` and it has a `basket_id`.
3. Confirm the basket exists with `status == checked_out`, `payment.basket_id == basket.id`, and both share the same `customer_id`.
4. Confirm a `three_ds` object exists and `three_ds.attempts < three_ds.max_attempts` (this workspace allows up to 2 attempts).
5. Check `three_ds.status` against the table, verbatim from `/docs/payments/3ds.md`:

   > - `3ds-status1`: a fresh challenge is already active. Do not start another challenge before the payment `three_ds.retry_after` timestamp. Use `/bin/date`; if the current time is earlier than `retry_after`, leave the payment unchanged and tell the customer when retry is available. If current time is at or after `retry_after`, a fresh challenge may be started if attempts remain.
   > - `3ds-status2`: the previous challenge was abandoned by the customer. This is recoverable if attempts remain.
   > - `3ds-status3`: the previous challenge timed out. This is recoverable if attempts remain.

   For `3ds-status1`, pull `/bin/date` (see [date_and_time](date_and_time.md)) and compare against `three_ds.retry_after`: before it → `OUTCOME_NONE_UNSUPPORTED` (tell the customer when retry is available); at/after it → eligible if attempts remain.
6. When every gate passes, call `/bin/payments recover-3ds <payment_id>`. Per `/docs/payments/3ds.md`, the command keeps `status == requires_3ds_action`, sets `three_ds.status` to `3ds-status1`, increments `three_ds.attempts`, and writes a new `three_ds.retry_after` (30-minute delay). Do not mark the payment `paid`, do not bypass 3DS, and do not run `/bin/checkout` on the already-checked-out basket.
7. Re-read `/proc/payment-ledger/<id>.json` and confirm `status` is still `requires_3ds_action` with a fresh `three_ds` challenge (incremented attempts, new `retry_after`) before `OUTCOME_OK`.
8. As part of evaluation, read `/docs/checkout.md` (it is a named prerequisite); surface any caveat that would flip the outcome to `OUTCOME_NONE_UNSUPPORTED`.

## Applied policies

When ownership matched, the applied policy set is **three** docs: `/docs/security.md` (identity), `/docs/checkout.md` (prerequisite), and `/docs/payments/3ds.md` (topic). The only branch that drops `/docs/checkout.md` is the cross-boundary `OUTCOME_DENIED_SECURITY`, where identity stopped the flow before checkout eligibility.

## Outcomes

- `OUTCOME_OK`: all gates passed, `/bin/payments recover-3ds` ran, post-state confirms a fresh challenge with payment still `requires_3ds_action`. Refs: `/docs/security.md`, `/docs/checkout.md`, `/docs/payments/3ds.md`, plus the customer's own payment and linked basket.
- `OUTCOME_DENIED_SECURITY`: identity does not match (foreign payment, claimed identity, override claim). **Do not mutate.** Cross-boundary refs are policy-docs only: `["/docs/security.md", "/docs/payments/3ds.md"]`.
- `OUTCOME_NONE_UNSUPPORTED`: identity matches but any of — payment not `requires_3ds_action`, no `basket_id`/`three_ds`, basket not `checked_out`, basket_id/customer mismatch, attempts exhausted, `3ds-status1` before `retry_after` — **or** an employee identity (`/docs/employees.md`). **Do not mutate.** Refs include `/docs/security.md`, `/docs/checkout.md`, `/docs/payments/3ds.md`, plus the owned payment and linked basket.

## Evidence ledger

`policy_docs_applied`:

- Ownership matched: `/docs/security.md`, `/docs/checkout.md`, `/docs/payments/3ds.md`.
- Customer cross-boundary denial: `/docs/security.md` plus the topic doc `/docs/payments/3ds.md` only.

`action_targets`:

- `/proc/payment-ledger/<id>.json` payment target; linked `/proc/carts/<id>.json` checked-out basket.

`answer_records`:

- Owned payment and linked basket when ownership passed and they decide recoverability or unsupported state.

`post_state_records`:

- `/proc/payment-ledger/<id>.json` re-read after `recover-3ds` to prove the fresh challenge before `OUTCOME_OK`.

`considered_not_cited`:

- Foreign payment/cart records in a cross-boundary denial; unrelated payment/cart candidates.

`refs_must_include`:

- Ownership-matched OK/unsupported: `/docs/security.md`, `/docs/checkout.md`, `/docs/payments/3ds.md`, the owned payment, and the linked basket.
- `OUTCOME_OK`: post-state payment path (deduped with the payment target).
- Cross-boundary denial: `["/docs/security.md", "/docs/payments/3ds.md"]`.

`refs_must_not_include`:

- Foreign payment/cart records in cross-boundary denials, `/docs/checkout.md` on identity-stop denials, and `bin-help` paths.

## Anti-patterns

From `/docs/payments/3ds.md`, forbidden even when other gates pass:

- Marking the payment `paid`, bypassing 3DS, or running `/bin/checkout` again on the checked-out basket.
- Recovering a `3ds-status1` payment before its `three_ds.retry_after` (use `/bin/date`).
- Recovering when `three_ds.attempts >= three_ds.max_attempts`.

Other anti-patterns:

- Treating an employee identity's recovery request as a security denial — it is `OUTCOME_NONE_UNSUPPORTED` (`/docs/employees.md`).
- Looking for `/bin/payments approve-refund` / `refund` — those verbs no longer exist; refunds use `/bin/refund` (see [returns](returns.md)).
- Citing a foreign payment/cart in refs because the request quoted the id.
- Dropping `/docs/checkout.md` from OK / authorized-unsupported refs because `/bin/checkout` was not run — it is a named prerequisite that gated the decision.
- Comparing `3ds-status1`'s `retry_after` without first pulling `/bin/date`.

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived.

- `/docs/payments/3ds.md` — full gate set, the 3DS status table, the `retry_after`/30-minute behaviour, the 2-attempt cap, the forbidden actions, and the prerequisite line naming `/docs/security.md` and `/docs/checkout.md`.
- `/docs/checkout.md` — prerequisite policy 3DS recovery defers to.
- `/docs/security.md` — identity / cross-boundary rule cited on both the denial branch and the ownership-matched bundle.
- `/bin/payments` (`--help`) — tool signature; this BP authorises `recover-3ds` only.
- `/bin/date` (`--help`) — trusted clock for the `3ds-status1` retry window.
- `payment-ledger` (`/proc/payment-ledger`) — payment `status`, `customer_id`, `basket_id`, and the `three_ds` object (`status`, `attempts`, `max_attempts`, `retry_after`).
- `carts` (`/proc/carts`) — linked basket `id`, `status`, and `customer_id`.
