# bp_returns v0007

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-18T00:57:20+00:00`
- parent: `v0006`

## Rationale

The trial asked to approve the refund for a return whose status was replacement_pending (not approved), with a linked payment. The correct outcome is OUTCOME_NONE_UNSUPPORTED, which the Executor reached — but it short-circuited: it read only the return record, jumped straight to the status gate, and never read the linked payment record. The grader failed the answer (0.0%) for a single missing required reference: the linked payment under /proc/payments/. The v0006 process listed reading the linked payment as a gate but its refs ledger phrased it as conditional ('the linked payment read for the paid gate'), giving textual cover to omit it once another gate failed first. This edit makes the gate inputs one evidence set that must be gathered before deciding (run /bin/id, read the return, read the linked /proc/payments/<return.payment_id>.json) and makes the linked payment a mandatory refs record on the authorized-OK / authorized-unsupported branch — even when an earlier gate such as return status already fails. Generalises to any refund-approval/finalization evaluation, not this trial's ids.

## Rollback

Create a new version from v0006 content (restoring the conditional 'linked payment read for the paid gate' wording) if the no-short-circuit / always-cite-linked-payment rule over-includes the payment in branches where it should not appear, e.g. pure cross-boundary denials.

## Dependencies
- `workspace:/docs/returns.md` — Authoritative refund-workflow policy: the four/five-gate sets (including the linked-payment paid gate) and the role/status enums that this edit operationalises as a no-short-circuit, always-read-and-cite-the-payment rule.
- `workspace:/docs/security.md` — Identity/ownership/role rule named verbatim as a prerequisite by /docs/returns.md; part of the applied-policy bundle and refs whenever the refund flow is evaluated.
- `bin_help:payments.help.txt` — Tool signatures for approve-refund <return_id> and refund <return_id>; if a new return-mutating verb appears the Process/Tools sections must be re-derived.
- `sql_table:return_requests` — Return id, return_status, reason code, and basket/payment/customer foreign keys used for bulk triple reconciliation; status enum drives the gate text.
- `sql_table:payment_transactions` — payment_status (the paid gate) and basket/customer links; the linked payment is the record this edit forces to be read and cited.
- `sql_table:shopping_baskets` — Basket ownership (customer_id) used by the finalization triple check referenced in Process C.
- `sql_table:payment_transaction_items` — Surviving line snapshot for archived payments during information/reconciliation lookups described in the archived-payment note.
- `workspace:/proc/returns/README.md` — Return status vocabulary and reconciliation keys; source for the status tokens enumerated in the gates.
- `workspace:/proc/payments/README.md` — Archived-payment semantics (basket_archived, cold-storage baskets, payment line snapshots) referenced by the reconciliation and finalization gates.
