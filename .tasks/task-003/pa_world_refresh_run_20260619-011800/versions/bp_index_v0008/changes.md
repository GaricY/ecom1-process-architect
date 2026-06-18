# bp_index v0008

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-18T22:24:20+00:00`
- parent: `v0007`

## Rationale

A new mutating runtime tool (/bin/account-recovery) plus a new /docs/security.md customer-only account-recovery rule create a distinct domain that the process map did not route. Added a §1 routing row pointing at the new business_processes/account_recovery.md and a §9 cross-cutting note (customer-only; 'recovery' is authority bait). All other rows, principles, outcome tokens, and the mutation gate are unchanged.

## Rollback

Retire this version to fall back to v0007: drop the account_recovery routing row and the §9 note.
