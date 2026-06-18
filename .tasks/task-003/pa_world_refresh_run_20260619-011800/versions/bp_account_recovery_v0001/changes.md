# bp_account_recovery v0001

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-18T22:24:20+00:00`

## Rationale

New mutating capability /bin/account-recovery (send-email-link <customer_id> <destination_email>) writes /run/actions/account-recovery-<customer_id>.json and is pinned by a new /docs/security.md rule making account recovery / email-change verification customer-only (link only to the account matching /bin/id). A mutating tool with its own gate, output file, and policy is a distinct atomic domain — separate from identity_and_auth (the general identity/ownership gate, which this BP applies via link) and from payments_3ds_recovery (payment recovery, not account recovery). The tool README states it 'does not enforce /docs/security.md', so a BP must.

## Rollback

Remove bp_account_recovery from the registry and drop its bp_index routing row and §9 note; no other unit depends on it.

## Dependencies
- `workspace:/docs/security.md` — Authoritative customer-only account-recovery / email-change rule and the matching-account requirement this BP enforces; also the source of the canonical denial incident pattern.
- `bin_help:account-recovery.help.txt` — Tool signature 'send-email-link <customer_id> <destination_email>' that the Process and Tools sections encode; a verb/arg change must trigger re-derivation.
- `sql_table:customer_accounts` — customer_id / customer_email shape used to confirm the actor's own account; a new verification/email-change status column would change the state gate.
