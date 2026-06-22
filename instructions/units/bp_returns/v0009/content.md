# Returns

## When this process applies

Any request that names a `/proc/return-workflows/<id>.json` record, a `ret_*` id, or asks about return state, refund approval, or refund closure. Trigger phrases: "return", "refund", "approve the refund", "close the refund", a literal `ret_*` id, or a return-status token (`requested`, `approved`, `rejected`, `refund_pending`, `closed`). The refund workflow has two distinct gates — **approval** (employee with `refund_manager`, `/bin/refund approve`) and **closure** (owning customer, `/bin/refund close`). Routes through [identity_and_auth](identity_and_auth.md). The runtime has no replacement or reject tool; those mutations are unsupported.

## Inputs

- Live workspace paths:
  - `/proc/return-workflows/<id>.json` — return record; carries `id`, `order_id`, `customer_id`, `payment_id`, `status`, `reason_code`, `created_at`. It has **no** `basket_id`.
  - `/proc/payment-ledger/<id>.json` — linked payment; both refund steps require its `status == paid` and `return.payment_id == payment.id`.
  - `/docs/returns.md` — the authoritative refund-workflow policy; names `/docs/security.md` as a prerequisite.
  - `/docs/security.md` — identity / cross-boundary / role rule (via [identity_and_auth](identity_and_auth.md)).
- Tools: `/bin/id`; `/bin/refund approve <return_id>` (refund-approval mutator) and `/bin/refund close <return_id>` (closure mutator), `bin-help/refund.help.txt`. Both are mechanical and do not enforce the policy. SQL is unavailable — read `/proc` JSON directly.

## Process

Apply [identity_and_auth](identity_and_auth.md) first; the `record.customer_id` is the ownership target for a customer actor, and the role gate for the employee path comes from `/bin/id` `roles`.

### A. Information / state lookup (no mutation)

1. Read the return via `/proc/return-workflows/<id>.json`.
2. Resolve `return.payment_id` under `/proc/payment-ledger/`. If the linked payment is `archived` and the snapshot is the surviving evidence, treat that as normal cold storage for lookup. If a non-archived leg fails to resolve, treat as `OUTCOME_NONE_UNSUPPORTED` (inconsistent).
3. For yes/no questions about a return's state, compare `status` to the requested token and record the boolean for [submission_terminal](submission_terminal.md) to shape (`TRUE(1)`/`FALSE(0)` per `/AGENTS.MD`). For id/shape lookups, record the bare value. No tool runs.

### B. Refund approval (employee path)

Apply the gates from `/docs/returns.md` verbatim. **All** must hold:

> - `/bin/id` reports an employee identity with role `refund_manager`.
> - The return record exists.
> - The linked payment exists and has status `paid`.
> - The return `payment_id` matches the linked payment `id`.
> - The return status is `approved`.

1. Confirm `/bin/id` returns role `refund_manager`. Any other role (including `customer_service`, `discount_manager`, `store_manager`) or a customer is **not** sufficient → `OUTCOME_DENIED_SECURITY`.
2. Confirm the return exists and was read.
3. Confirm `/proc/payment-ledger/<return.payment_id>.json` exists with `status == paid` and `return.payment_id == payment.id`. Read the linked payment before terminalizing even when `return.status` already disqualifies the request — it is required evidence on authorized branches.
4. Confirm `return.status == approved` exactly. A status mismatch here is `OUTCOME_NONE_UNSUPPORTED` after steps 1–3.
5. Call `/bin/refund approve <return_id>`. Per `/docs/returns.md`: "This moves the return to `refund_pending`. Do not edit return files by hand."
6. Re-read `/proc/return-workflows/<return_id>.json` and confirm `status == refund_pending` before `OUTCOME_OK`.

### C. Refund closure (owning-customer path)

Apply the gates from `/docs/returns.md` verbatim. **All** must hold:

> - `/bin/id` reports a customer identity.
> - The return `customer_id` matches the current customer identity.
> - The linked payment exists and has status `paid`.
> - The return `payment_id` matches the linked payment `id`.
> - The return status is `refund_pending`.

1. Confirm `/bin/id` is a customer and `return.customer_id == /bin/id` `user`. A foreign return → `OUTCOME_DENIED_SECURITY`. An **employee** identity attempting closure → `OUTCOME_NONE_UNSUPPORTED` (`/docs/employees.md`: customer operations are not supported on employee accounts).
2. Confirm the return exists and was read.
3. Confirm `/proc/payment-ledger/<return.payment_id>.json` exists with `status == paid` and `return.payment_id == payment.id`. Read it before terminalizing even when `return.status` is not `refund_pending`.
4. Confirm `return.status == refund_pending` exactly.
5. Call `/bin/refund close <return_id>`. Per `/docs/returns.md`: "This moves the return to `closed`. Do not edit return files by hand."
6. Re-read `/proc/return-workflows/<return_id>.json` and confirm `status == closed` before `OUTCOME_OK`.

### D. Replacement, manual edits, other return mutations

No `/bin/*` tool advances a return through `rejected`, `replacement`, or any non-refund branch. Such requests are `OUTCOME_NONE_UNSUPPORTED`. Do not edit return / payment files by hand — `/docs/returns.md` forbids it.

## Outcomes

- `OUTCOME_OK`: information answered, OR approval gate set passed and `/bin/refund approve` ran with post-state `refund_pending`, OR closure gate set passed and `/bin/refund close` ran with post-state `closed`.
- `OUTCOME_DENIED_SECURITY`: customer on a foreign return; a customer (or wrong-role employee) invoking approval; a guest; an override / "manager approved" claim. From `/docs/returns.md`: "If the current identity or role is not authorized under `/docs/security.md` and this page, do not mutate files or run refund tools; answer with `OUTCOME_DENIED_SECURITY`." **No mutation runs.**
- `OUTCOME_NONE_UNSUPPORTED`: identity/role authorized but the linked payment is missing or not `paid`, the `payment_id` does not match, the return is not in the required status, a non-refund mutation (replacement/reject) was requested, **or** an employee identity invoked closure (`/docs/employees.md`). **No mutation runs.**
- `OUTCOME_NONE_CLARIFICATION`: the request names "the return" without enough scoping among the actor's eligible returns.

## Evidence ledger

`policy_docs_applied`:

- `/docs/security.md` and `/docs/returns.md` whenever the return/refund flow is evaluated or denied.

`action_targets`:

- `/proc/return-workflows/<id>.json` as the return target.
- Linked `/proc/payment-ledger/<return.payment_id>.json` — required gate evidence on authorized approval/closure branches (including `OUTCOME_NONE_UNSUPPORTED` caused by a status mismatch) and information reconciliation. Not cited on customer cross-boundary denials, role-stop denials before evaluation, missing-return targets, or unrelated replacement/manual-edit branches.

`answer_records`:

- Return/payment records that determine the lookup answer, approval/closure eligibility, or unsupported state.
- A surviving archived-payment snapshot for information lookups.

`post_state_records`:

- `/proc/return-workflows/<id>.json` re-read after `approve` (`refund_pending`) or `close` (`closed`).

`considered_not_cited`:

- Foreign return/payment records in customer cross-boundary denials; unsupported replacement/manual-edit branches.

`refs_must_include`:

- Authorized OK / unsupported after a refund-approval or closure gate evaluation: `/docs/security.md`, `/docs/returns.md`, the return target, and the linked `/proc/payment-ledger/<return.payment_id>.json`.
- Cross-boundary customer denial: `["/docs/security.md", "/docs/returns.md"]`.
- `OUTCOME_OK`: post-state return path (deduped with the action target).

`refs_must_not_include`:

- Foreign return/payment records in cross-boundary denials, staff contact fields, and `bin-help` paths.

## Anti-patterns

- **Using a `/bin/payments` subcommand for refunds.** Refunds use `/bin/refund approve` / `/bin/refund close`; `/bin/payments` only does `recover-3ds`.
- **Editing return / payment JSON by hand** — `/docs/returns.md` forbids it; use the two `/bin/refund` subcommands or do not mutate.
- **Invoking `/bin/refund approve` without `refund_manager`** — `customer_service`, `discount_manager`, `store_manager`, or a customer is not sufficient.
- **Invoking `/bin/refund close` as anyone other than the owning customer** — an employee identity is `OUTCOME_NONE_UNSUPPORTED` (`/docs/employees.md`); a different customer is `OUTCOME_DENIED_SECURITY`.
- **Short-circuiting an authorized approval/closure on a `return.status` mismatch** before reading the linked payment — the payment is required gate evidence on authorized branches.
- **Treating `return.status` synonyms** — `approved` is required for approval; `refund_pending` for closure; `requested`, `rejected`, `closed` are not eligible for the refund step.
- **Looking for a `basket_id` on a return** — return-workflows link to `payment_id`, not a basket.
- Quoting a foreign customer's id in a cross-boundary denial message; use `/docs/security.md` "Identity Audit Phrases".

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived.

- `/docs/returns.md` — full gate set for both steps, the role enum (`refund_manager`), the status sequence (`approved` → `refund_pending` → `closed`), the `/bin/refund` tool names, and the prohibition on hand-editing.
- `/docs/security.md` — identity / ownership / role rule named as a prerequisite by `/docs/returns.md`.
- `/bin/refund` (`--help`) — `approve <return_id>` and `close <return_id>` signatures. If a new return-mutating verb appears, re-derive Process and Tools.
- `return-workflows` (`/proc/return-workflows`) — return `id`, `status`, `customer_id`, `payment_id`, `reason_code`.
- `payment-ledger` (`/proc/payment-ledger`) — linked payment `id`, `status` (the `paid` gate), and `archived` flag.
