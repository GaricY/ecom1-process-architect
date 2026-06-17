# bp_payments_3ds_recovery v0006

- mode: `refresh`
- created_by: `codex`
- created_at: `2026-05-26T08:22:43+00:00`
- parent: `v0005`

## Rationale

Add an explicit policy_update_scan handoff for 3DS topic-folder and cross-workflow updates while keeping 3DS recovery gates local.

## Rollback

Create a new version from v0005 if the helper handoff misses topic-folder payment updates.

## Dependencies
- `workspace:/docs/payments/3ds.md` — 3DS recovery gate set, status table, forbidden actions, and prerequisite policy bundle.
- `workspace:/docs/checkout.md` — Prerequisite checkout policy named by the 3DS doc.
- `workspace:/docs/security.md` — Identity/cross-boundary prerequisite named by the 3DS doc.
- `bin_help:payments.help.txt` — Tool signature for recover-3ds and sibling payment subcommands.
