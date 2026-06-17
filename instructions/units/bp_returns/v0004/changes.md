# bp_returns v0004

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-28T18:31:45+00:00`
- parent: `v0003`

## Rationale

Schema rename. The bulk-reconciliation SQL joins the renamed triple returns/baskets/payments -> return_requests/shopping_baskets/payment_transactions, and the SQL cite column path -> record_path. Verbatim /docs/returns.md approval/finalization gate quotes and the unchanged JSON record field names (status, customer_id, basket_id, payment_id) were preserved. Added sql_table dependencies for the reconciliation triple so future shape changes trigger review.

## Rollback

Restore bp_returns v0003 content (returns/baskets/payments join names, path cite) and drop the added sql_table dependencies if the rename mapping proves wrong.

## Dependencies
- `workspace:/docs/returns.md` — Full gate set for both refund workflow steps, the refund_manager role, the status sequence, and the no-hand-edit prohibition.
- `workspace:/docs/security.md` — Identity/ownership/role rule named verbatim as a prerequisite by /docs/returns.md; cited in the applied-policy bundle whenever the refund flow was evaluated.
- `bin_help:payments.help.txt` — Tool signatures for approve-refund <return_id> and refund <return_id>.
- `sql_table:return_requests` — Return id, return_status, reason code, and basket/payment/customer foreign keys used for bulk triple reconciliation.
- `sql_table:payment_transactions` — payment_status (paid gate) and basket/customer links read during reconciliation.
- `sql_table:shopping_baskets` — Basket ownership (customer_id) used by the finalization triple check.
