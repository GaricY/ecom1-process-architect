# bp_payments_3ds_recovery v0010

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-30T09:37:50+00:00`
- parent: `v0009`

## Rationale

3ds.md was rewritten: recovery is now an owning-customer action (payment customer_id matches /bin/id) rather than a basket-status-only gate; 3ds-status1 is now recoverable once the payment three_ds.retry_after passes (checked against /bin/date) instead of being permanently non-recoverable; the 2-attempt cap and a 30-minute retry delay are documented; payment family /proc/payments -> /proc/payment-ledger, basket /proc/baskets -> /proc/carts; 3DS fields live in payment_three_ds; /proc/payments/README.md removed; /bin/payments now carries only recover-3ds.

## Rollback

Restore v0009 content (3ds-status1 always non-recoverable, no retry_after/customer-identity gate, /proc/payments + /proc/baskets, /proc/payments/README.md dependency).

## Dependencies
- `workspace:/docs/payments/3ds.md` — Full gate set, the customer-identity gate, retry_after/3ds-status1 semantics, the 2-attempt cap, the recover-3ds invocation, and the security.md+checkout.md prerequisite line.
- `workspace:/docs/checkout.md` — Prerequisite policy that 3DS recovery defers to.
- `workspace:/docs/security.md` — Identity/cross-boundary rule named in the 3DS prerequisite line.
- `bin_help:payments.help.txt` — Tool signature; this BP authorises recover-3ds only (refund subcommands have moved off this binary).
- `bin_help:date.help.txt` — Trusted clock for retry_after / lockout comparison.
- `sql_table:payment_ledger` — Payment status, customer_id, basket_id, archive shape.
- `sql_table:payment_three_ds` — status/attempts/max_attempts/retry_after read for the recovery gate.
- `sql_table:carts` — Linked basket status==checked_out and customer_id match.
