# Basket Lifecycle

## When this process applies

Any request that reads, names, or asks about a `/proc/carts/<id>.json` record. Trigger phrases: "my basket", "the latest basket", a literal cart id, "basket status", or as a preliminary read inside [checkout](checkout.md), [discount](discount.md), [payments_3ds_recovery](payments_3ds_recovery.md). This BP is the **state registry** — it does not mutate; sibling BPs do.

## Inputs

- Live workspace paths:
  - `/proc/carts/<id>.json` — the cart record being read.
  - `/proc/payment-ledger/<id>.json` — archived-payment context where older payments can outlive their cart file.
  - `/docs/checkout.md` — basket lifecycle and "latest active basket" semantics.
- Tools: `/bin/id` (ownership), `/bin/date` (recency, via [date_and_time](date_and_time.md)). SQL is unavailable — read JSON records directly with `ws.read` / `ws.find`.

**Record shape (from the reconstructed `/proc` projection).** A cart carries:
`id`, `customer_id`, `store_id`, `status`, `created_at`, `lines[]` (each `{sku, quantity}`), and an optional `discount` object (`{percent, reason_code, issuer_id}`). There is no SQL projection and no `record_path` column; the cite path is the live `/proc/carts/...json` path you read.

## Process

1. Apply [identity_and_auth](identity_and_auth.md). For a customer actor, verify `record.customer_id == /bin/id` `user` before reading or citing it; a foreign cart → `OUTCOME_DENIED_SECURITY` and the path stays out of refs.
2. Read the record and note `id, customer_id, store_id, status, created_at`, `lines[]`, and any `discount` object.
3. Determine state:
   - `active` → eligible target for [checkout](checkout.md) item-edits and checkout, and for [discount](discount.md). May still fail downstream gates.
   - `checked_out` → historical order. Re-running `/bin/checkout` on it is forbidden. Eligible target for [payments_3ds_recovery](payments_3ds_recovery.md).
   - Other statuses (e.g. abandoned/guest baskets) are not editable or checkout-eligible per `/docs/checkout.md`.
4. For "the latest / newest active basket" wording, use the active basket with the latest `created_at` (`/docs/checkout.md`). For item edits this alone resolves "my basket"; do not ask for clarification just because the customer has several active baskets. For a **checkout** of "my basket" with more than one active basket possible, the request is ambiguous — see [checkout](checkout.md).
5. Cart lines carry **no availability flag** — adding an item never reserves stock. Whenever checkout eligibility matters, re-check same-day availability at the cart `store_id` (`max(on_hand - reserved, 0)`); see [availability_and_inventory](availability_and_inventory.md).
6. Archived-payment context: a `/proc/payment-ledger` record may have `archived: true`, its cart file aged out, and the payment carries its own `lines` snapshot. If a missing cart id came from a linked payment, check the payment `archived` flag before treating the missing file as inconsistent.

## Outcomes

- This BP produces no final outcome on its own; the invoking sibling BP does.
- If the cart id named in the request does not exist, the sibling BP submits `OUTCOME_NONE_UNSUPPORTED` (missing) or `OUTCOME_NONE_CLARIFICATION` (ambiguous), except when the id is linked from an archived payment whose snapshot is the surviving evidence.

## Evidence ledger

`actor_or_protocol_evidence`:

- `/bin/id` result from `identity_and_auth` for customer ownership or employee action-target branching.

`action_targets`:

- `/proc/carts/<id>.json` when the cart is the requested target or a target selected for a sibling workflow.

`answer_records`:

- The owned cart record when answering status, discount presence, latest basket, or lifecycle questions.
- Candidate owned carts on true clarification outcomes.

`considered_not_cited`:

- Foreign carts located for a cross-boundary denial.
- Missing cart paths linked from archived payments when the payment snapshot is the evidence.

`refs_must_include`:

- `/proc/carts/<id>.json` only if ownership passed for a customer actor or it is an employee action target.
- Each owned candidate cart path on `OUTCOME_NONE_CLARIFICATION`.

`refs_must_not_include`:

- Foreign customer cart paths and rejected/ambiguous candidates the actor cannot see.

`post_state_records`:

- none in this BP; sibling mutating BPs own cart post-state reads.

## Anti-patterns

- Citing a foreign customer's cart path in refs because the request quoted the id.
- Treating any phrase as a basket state. The only states are the `status` field values (`active`, `checked_out`, …).
- Assuming a cart line is available because the cart exists — lines have no availability flag. Re-check `max(on_hand - reserved, 0)` for `(store_id, sku)`.
- Treating `created_at` from a stale read as "now"; recency comparisons use `/bin/date`. See [date_and_time](date_and_time.md).
- Trying to read a `/proc/customers` record for ownership — none exists; compare `customer_id` against `/bin/id`.

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived.

- `/docs/checkout.md` — cart status semantics and the "latest active basket" rule.
- `carts` (`/proc/carts`) — cart id, status, store pointer, created-at, lines, and discount object shape read by this registry.
- `payment-ledger` (`/proc/payment-ledger`) — `archived` flag and payment line snapshot for the cold-storage cart case.
