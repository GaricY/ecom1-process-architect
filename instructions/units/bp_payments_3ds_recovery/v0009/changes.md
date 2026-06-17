# bp_payments_3ds_recovery v0009

- mode: `world_refresh`
- created_by: `codex`
- created_at: `2026-05-29T11:30:59+00:00`
- parent: `v0008`
- no_semantic_change: revalidated against the new dependency hashes without text edits

## Rationale

Attach /proc/payments/README.md as the drift dependency for payment record status and 3DS field semantics. Executor-visible 3DS policy text is unchanged.

## Rollback

Revert to v0008 if payment record README drift should be tracked only through another payment-oriented BP.

## Dependencies
- `workspace:/docs/payments/3ds.md` — Full gate set, legacy 3DS status table, forbidden actions, and the prerequisite line naming /docs/security.md and /docs/checkout.md.
- `workspace:/docs/checkout.md` — Prerequisite policy that 3DS recovery defers to; part of the ownership-matched three-doc refs bundle.
- `workspace:/docs/security.md` — Identity / cross-boundary rule named alongside checkout in the 3DS prerequisite line; cited on both the cross-boundary denial and the ownership-matched bundle.
- `bin_help:payments.help.txt` — Tool signature; this BP authorises recover-3ds only and excludes approve-refund/refund.
- `workspace:/proc/payments/README.md` — Payment record status/3DS field semantics and archived-payment context.
