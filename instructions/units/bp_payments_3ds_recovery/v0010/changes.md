# bp_payments_3ds_recovery v0010

- mode: `manual_refactor`
- created_by: `human`
- created_at: `2026-06-18T00:31:55+00:00`
- parent: `v0009`

## Rationale

Refactor refs from a flat scratchpad list into typed Evidence ledger roles. refs.md owns the shared model and safety projection; topic BPs classify their domain evidence; submission_terminal checks the completed ledger before submit.

## Rollback

Retire this version to fall back to v0009, or issue a new manual_refactor version with adjusted ledger wording.

## Dependencies
- `workspace:/docs/payments/3ds.md` — Full gate set, legacy 3DS status table, forbidden actions, and the prerequisite line naming /docs/security.md and /docs/checkout.md.
- `workspace:/docs/checkout.md` — Prerequisite policy that 3DS recovery defers to; part of the ownership-matched three-doc refs bundle.
- `workspace:/docs/security.md` — Identity / cross-boundary rule named alongside checkout in the 3DS prerequisite line; cited on both the cross-boundary denial and the ownership-matched bundle.
- `bin_help:payments.help.txt` — Tool signature; this BP authorises recover-3ds only and excludes approve-refund/refund.
- `workspace:/proc/payments/README.md` — Payment record status/3DS field semantics and archived-payment context.
