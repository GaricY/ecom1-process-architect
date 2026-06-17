# bp_privacy_and_disclosure v0003

- mode: `world_refresh`
- created_by: `codex`
- created_at: `2026-05-29T11:30:59+00:00`
- parent: `v0002`

## Rationale

Clarify customer home coordinates as coarse home-area risk context while preserving privacy treatment; add /proc/customers/README.md dependency.

## Rollback

Revert to v0002 if the added coordinate wording weakens privacy treatment in practice.

## Dependencies
- `workspace:/docs/security.md` — Personal-information and cross-boundary disclosure rule.
- `bin_help:id.help.txt` — Actor output shape for ownership/disclosure branching.
- `sql_table:customer_accounts` — Customer contact/profile fields (customer_email, home_city, home_latitude, home_longitude) that are private by default.
- `sql_table:employee_accounts` — Employee roster, assigned store (store_id), and contact fields (employee_email, job_title).
- `workspace:/proc/customers/README.md` — Customer email and coarse home-area coordinate semantics.
