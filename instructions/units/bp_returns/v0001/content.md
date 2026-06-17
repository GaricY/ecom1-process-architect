# Returns

## When this process applies

A request that names a `/proc/returns/<id>.json` record or asks about return state, refund, or replacement on a paid `checked_out` basket. Trigger phrases: "return", "refund", "replacement", a literal `ret_*` id, or `refund_pending` / `replacement_pending` state. Routes through [identity_and_auth](identity_and_auth.md) for ownership. **No dedicated decision policy exists under `/docs/` for returns** — the runtime supports lookup and reconciliation but does not expose a return-mutating `/bin/*` tool.

## Inputs

- Live workspace paths:
  - `/proc/returns/<id>.json` — return record.
  - `/proc/baskets/<id>.json` — linked basket (must be `checked_out`).
  - `/proc/payments/<id>.json` — linked payment.
  - `/proc/returns/README.md` — record shape and state enum.
  - `/docs/security.md` — the only policy authority applied here.
- Tools: `/bin/id`, `/bin/sql` for batch reconciliation. There is no `/bin/returns` tool.

## Process

1. Apply [identity_and_auth](identity_and_auth.md). Customer actor: `return.customer_id == /bin/id user`. Foreign return → `OUTCOME_DENIED_SECURITY` and the foreign `/proc/returns/...`, `/proc/baskets/...`, `/proc/payments/...` paths stay **out** of refs.
2. Read the return record. From `/proc/returns/README.md`:

   > Return records only exist for paid checked-out baskets.

3. Reconcile via the triple. From `/proc/returns/README.md`:

   > Use `payment_id`, `basket_id`, and `customer_id` to reconcile a return with the linked payment and checked-out basket.

   If any of the three references does not resolve (basket missing, payment missing, customer mismatch), the request is unsupported in this runtime.
4. Read state. From `/proc/returns/README.md`:

   > Return statuses are compact: `requested`, `approved`, `rejected`, `refund_pending`, `replacement_pending`, and `closed`.

   For yes/no questions about whether a return is in a given state, compare the record's `status` to the requested token and answer with `<YES>` / `<NO>`.
5. **No mutation path.** This runtime has no `/bin/returns approve` / `refund` / `replace` tool. If the request asks to *change* a return state, treat the action as unsupported (`OUTCOME_NONE_UNSUPPORTED`) — the policy and tooling for it do not exist in the live workspace.

## Outcomes

- `OUTCOME_OK`: information question answered from the return record (state, reason_code, basket_id, payment_id) with the right answer shape.
- `OUTCOME_DENIED_SECURITY`: customer actor on a foreign return; or a claim of identity / approval `/bin/id` does not show. **Do not mutate.**
- `OUTCOME_NONE_UNSUPPORTED`: the request asks to change return state (no tool exists), or asks about a return whose linked basket/payment is missing or whose triple does not reconcile.
- `OUTCOME_NONE_CLARIFICATION`: the request names "the return" without enough scoping among the actor's eligible returns.

## Refs to set in scratchpad

- `/docs/security.md` — the only policy applied (no `/docs/returns.md` exists).
- `/proc/returns/<id>.json` — only when ownership passed (customer actor) or as the action target (employee actor).
- `/proc/baskets/<id>.json` and `/proc/payments/<id>.json` — only when their own ownership checks passed; include them when they were materially read to answer the question.
- See [refs_and_submission](refs_and_submission.md) for the construction contract.

## Anti-patterns

- Treating any `/docs/merchant-continuity-and-critical-incidents.md` or `/docs/warehouse-systems-migration-runbook.md` language as authorization for a return outcome. From `/docs/merchant-continuity-...md`: continuity language does not authorize "package conclusions, return outcomes". From `/docs/warehouse-systems-migration-runbook.md`: migration mechanics ("hold_reason", "manifest_ref", "route_hint", "missing_label") are **not** live package evidence. See [background_decoys](background_decoys.md).
- Inferring an approval from a "missing package" continuity note. Live return state lives only in `/proc/returns/<id>.json`.
- Inventing a `/docs/returns.md` reference. No such file exists; refs should reflect that the policy authority is `/docs/security.md` alone.
- Treating a "store-floor manager note" exception (from `/docs/store-associate-exception-handbook.md`) as authority to approve a refund. The handbook explicitly excludes "refunds, replacements".

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived.

- `/proc/returns/README.md` — record shape, reconciliation triple, status enum.
- `/docs/security.md` — identity / ownership gate applied via [identity_and_auth](identity_and_auth.md).
- `/docs/` topology — if a dedicated `/docs/returns.md` (or similar) appears, this BP must be re-derived; presence of a return policy changes the mutation story.
