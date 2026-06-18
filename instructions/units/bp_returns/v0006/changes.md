# bp_returns v0006

- mode: `manual_refactor`
- created_by: `human`
- created_at: `2026-06-18T00:26:47+00:00`
- parent: `v0005`

## Rationale

Refactor refs from a flat scratchpad list into typed Evidence ledger roles. refs.md owns the shared model and safety projection; topic BPs classify their domain evidence; submission_terminal checks the completed ledger before submit.

## Rollback

Retire this version to fall back to v0005, or issue a new manual_refactor version with adjusted ledger wording.

## Dependencies
- `workspace:/docs/returns.md` — Full gate set for both refund workflow steps, the refund_manager role, the status sequence, and the no-hand-edit prohibition.
- `workspace:/docs/security.md` — Identity/ownership/role rule named verbatim as a prerequisite by /docs/returns.md; cited in the applied-policy bundle whenever the refund flow was evaluated.
- `bin_help:payments.help.txt` — Tool signatures for approve-refund <return_id> and refund <return_id>.
- `sql_table:return_requests` — Return id, return_status, reason code, and basket/payment/customer foreign keys used for bulk triple reconciliation.
- `sql_table:payment_transactions` — payment_status (paid gate) and basket/customer links read during reconciliation.
- `sql_table:shopping_baskets` — Basket ownership (customer_id) used by the finalization triple check.
- `sql_table:payment_transaction_items` — Surviving line snapshot for archived payments during information/reconciliation tasks.
- `workspace:/proc/returns/README.md` — Return status vocabulary and reconciliation keys.
- `workspace:/proc/payments/README.md` — Archived-payment semantics: basket_archived, cold-storage baskets, and payment line snapshots.
