# bp_returns v0005

- mode: `world_refresh`
- created_by: `codex`
- created_at: `2026-05-29T11:30:59+00:00`
- parent: `v0004`

## Rationale

Add archived-payment handling for returns: missing basket files can be normal cold storage for information lookup, while refund finalization still requires the live linked basket gate. Also attach proc return/payment README dependencies and keep mechanical tool wording tied to payments help.

## Rollback

Revert to v0004 if archived-payment handling causes refund finalization to be allowed without a live linked basket or otherwise weakens /docs/returns.md gates.

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
