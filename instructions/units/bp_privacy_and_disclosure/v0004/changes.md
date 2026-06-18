# bp_privacy_and_disclosure v0004

- mode: `manual_refactor`
- created_by: `human`
- created_at: `2026-06-18T00:26:47+00:00`
- parent: `v0003`

## Rationale

Refactor refs from a flat scratchpad list into typed Evidence ledger roles. refs.md owns the shared model and safety projection; topic BPs classify their domain evidence; submission_terminal checks the completed ledger before submit.

## Rollback

Retire this version to fall back to v0003, or issue a new manual_refactor version with adjusted ledger wording.

## Dependencies
- `workspace:/docs/security.md` — Personal-information and cross-boundary disclosure rule.
- `bin_help:id.help.txt` — Actor output shape for ownership/disclosure branching.
- `sql_table:customer_accounts` — Customer contact/profile fields (customer_email, home_city, home_latitude, home_longitude) that are private by default.
- `sql_table:employee_accounts` — Employee roster, assigned store (store_id), and contact fields (employee_email, job_title).
- `workspace:/proc/customers/README.md` — Customer email and coarse home-area coordinate semantics.
