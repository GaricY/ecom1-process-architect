# bp_returns v0009

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-22T00:02:07+00:00`
- parent: `v0008`

## Rationale

returns.md rewritten: refund tools moved to /bin/refund approve / /bin/refund close (was /bin/payments approve-refund / refund); statuses approved -> refund_pending -> closed; closure now gates on customer-id + linked payment only (return-workflows has no basket_id, so the linked-basket gate is dropped). Records under /proc/return-workflows and /proc/payment-ledger. Employee invoking closure is unsupported (employees.md). SQL removed.

## Rollback

Restore bp_returns v0008 content with its /bin/payments refund tools, the linked-basket finalization gate, and shopping_baskets/payment_transactions SQL dependencies.

## Dependencies
- `workspace:/docs/returns.md` — Both-step gate set, refund_manager role, the approved->refund_pending->closed sequence, the /bin/refund tool names, and the no-hand-edit rule.
- `workspace:/docs/security.md` — Identity/ownership/role rule named as a prerequisite by returns.md.
- `bin_help:refund.help.txt` — approve <return_id> and close <return_id> signatures.
- `sql_table:return-workflows` — Return id, status, customer_id, payment_id, reason_code.
- `sql_table:payment-ledger` — Linked payment id, status (the paid gate), and archived flag.
