# bp_index v0008

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-18T23:08:58+00:00`
- parent: `v0007`

## Rationale

A new mutating capability (/bin/account-recovery) plus a new /docs/security.md customer-only rule create a new routable domain. Add a routing row for business_processes/account_recovery.md (Mutating: /bin/account-recovery send-email-link) and a cross-cutting principle so the executor reaches the new BP; the new tool is automatically covered by the §4 mutation gate via its Mutating-column entry.

## Rollback

Restore bp_index v0007 (drop the account_recovery routing row and principle 9); the rest of the index is unchanged.
