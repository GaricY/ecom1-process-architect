# bp_privacy_and_disclosure v0002

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-28T18:31:46+00:00`
- parent: `v0001`

## Rationale

Schema rename. The contact-field tables this BP names changed: customers->customer_accounts, employees->employee_accounts; the SQL cite column path->record_path (the 'citing *.path because SQL returned it' anti-pattern). Re-derived Inputs, the anti-pattern, and dependencies. The unchanged on-disk JSON field names (email, display_name, home_lat/home_lon, title) and the disclosure logic were preserved.

## Rollback

Restore bp_privacy_and_disclosure v0001 content and old sql_table dependencies (customers, employees) if the rename mapping proves wrong.

## Dependencies
- `workspace:/docs/security.md` — Personal-information and cross-boundary disclosure rule.
- `bin_help:id.help.txt` — Actor output shape for ownership/disclosure branching.
- `sql_table:customer_accounts` — Customer contact/profile fields (customer_email, home_city, home_latitude, home_longitude) that are private by default.
- `sql_table:employee_accounts` — Employee roster, assigned store (store_id), and contact fields (employee_email, job_title).
