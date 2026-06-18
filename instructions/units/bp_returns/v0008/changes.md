# bp_returns v0008

- mode: `manual_refactor`
- created_by: `human`
- created_at: `2026-06-18T09:04:42+00:00`
- parent: `v0007`

## Rationale

Remove generic answer-token wording from the returns topic BP. The returns process now records yes/no or identifier answer kind and domain facts, while submission_terminal owns the final message payload format.

## Rollback

Retire this version to fall back to v0007 if removing explicit topic-level payload wording causes return state answers to lose their required format.

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
