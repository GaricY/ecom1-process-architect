# bp_privacy_and_disclosure v0001

- mode: `initial_migration`
- created_by: `codex`
- created_at: `2026-05-26T08:22:43+00:00`

## Rationale

Create a focused privacy/disclosure BP for contact-data handling that identity/auth did not operationalize. It separates action authorization from whether customer or employee contact/profile fields may appear in messages or refs.

## Rollback

Remove this unit from registry and fold disclosure bullets back into identity_and_auth and refs if separate privacy routing overcomplicates simple trials.

## Dependencies
- `workspace:/docs/security.md` — Authority for personal-information and cross-boundary disclosure boundaries.
- `bin_help:id.help.txt` — Actor shape used for ownership/disclosure branching.
- `sql_table:customers` — Customer profile/contact fields whose disclosure this BP governs.
- `sql_table:employees` — Employee roster/contact/store fields whose disclosure this BP governs.
