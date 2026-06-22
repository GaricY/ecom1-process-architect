# bp_returns v0006

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-30T09:37:50+00:00`
- parent: `v0005`

## Rationale

returns.md moved the refund mutators from /bin/payments approve-refund|refund to /bin/refund approve|close; the customer closure gate dropped the linked-basket requirement (now: customer identity, return customer_id match, payment paid, payment_id match, status refund_pending); families renamed /proc/returns -> /proc/return-workflows and /proc/payments -> /proc/payment-ledger; both steps require return.payment_id == payment.id; /proc/returns/README.md and /proc/payments/README.md removed; /bin/sql down -> reconcile over /proc JSON.

## Rollback

Restore v0005 content (/bin/payments approve-refund|refund, the linked-basket finalization gate, /proc/returns + /proc/payments, SQL return_requests/payment_transactions reconciliation).

## Dependencies
- `workspace:/docs/returns.md` — Both gate sets, refund_manager role, the approved->refund_pending->closed sequence, the /bin/refund invocations, and the prohibition on editing return files by hand.
- `workspace:/docs/security.md` — Identity/ownership/role rule named verbatim as a prerequisite by returns.md.
- `bin_help:refund.help.txt` — Tool signatures for approve <return_id> and close <return_id> (replaces the retired /bin/payments approve-refund|refund).
- `bin_help:payments.help.txt` — Confirms /bin/payments no longer carries refund verbs (only recover-3ds).
- `sql_table:return_workflows` — Return id, status, payment_id, customer_id, order_id for reconciliation.
- `sql_table:payment_ledger` — status (paid gate), customer_id, archive shape, and surviving lines snapshot.
