# bp_payments_3ds_recovery v0012

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-22T00:02:07+00:00`
- parent: `v0011`

## Rationale

3ds.md rewritten: eligibility now keys on payment.customer_id == /bin/id (not /proc/baskets ownership); records live under /proc/payment-ledger and /proc/carts; 2-attempt cap; 3ds-status1 gated on three_ds.retry_after vs /bin/date with a 30-minute new-challenge delay. /bin/payments now exposes only recover-3ds (refund verbs moved to /bin/refund). Replaced the old dated-update lockout flow with the doc's native retry_after logic. Customer-only; employee identity is unsupported (employees.md). SQL removed.

## Rollback

Restore bp_payments_3ds_recovery v0011 content with its /proc/baskets ownership, policy_update_scan lockout flow, and /bin/payments refund anti-patterns.

## Dependencies
- `workspace:/docs/payments/3ds.md` — Gate set, 3DS status table, retry_after/30-minute behaviour, 2-attempt cap, and the security.md+checkout.md prerequisite line.
- `workspace:/docs/checkout.md` — Prerequisite policy 3DS recovery defers to.
- `workspace:/docs/security.md` — Identity / cross-boundary rule cited on the denial branch and the ownership-matched bundle.
- `bin_help:payments.help.txt` — Tool signature; this BP authorises recover-3ds only.
- `bin_help:date.help.txt` — Trusted clock for the 3ds-status1 retry_after window.
- `sql_table:payment-ledger` — Payment status, customer_id, basket_id, and the three_ds object.
- `sql_table:carts` — Linked basket id, status, and customer_id.
