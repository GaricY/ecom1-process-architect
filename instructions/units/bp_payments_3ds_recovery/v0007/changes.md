# bp_payments_3ds_recovery v0007

- mode: `refresh`
- created_by: `codex`
- created_at: `2026-05-26T08:53:50+00:00`
- parent: `v0006`

## Rationale

Remove duplicated policy-update scan mechanics from the 3DS recovery BP. It now passes payment-specific context to policy_update_scan and keeps only 3DS gates and interpretation of matched updates local.

## Rollback

Create a new version from v0006 if moving scan mechanics into policy_update_scan causes missed 3DS policy updates.

## Dependencies
- `workspace:/docs/payments/3ds.md` — 3DS recovery gate set, status table, forbidden actions, and prerequisite policy bundle.
- `workspace:/docs/checkout.md` — Prerequisite checkout policy named by the 3DS doc.
- `workspace:/docs/security.md` — Identity/cross-boundary prerequisite named by the 3DS doc.
- `bin_help:payments.help.txt` — Tool signature for recover-3ds and sibling payment subcommands.
