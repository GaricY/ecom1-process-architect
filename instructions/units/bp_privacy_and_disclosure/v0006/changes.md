# bp_privacy_and_disclosure v0006

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-22T00:02:07+00:00`
- parent: `v0005`

## Rationale

SQL is gone and there is no customer_accounts table or /proc/customers family, so customer email/home-coordinate disclosure content no longer applies. Re-centered on the live private surface: staff contact details. security.md now forbids customers/guests receiving direct employee contact details or employee profile references as a workaround; /docs/employees.md separates employee and customer accounts.

## Rollback

Restore bp_privacy_and_disclosure v0005 content and its customer_accounts/employee_accounts SQL and /proc/customers/README dependencies.

## Dependencies
- `workspace:/docs/security.md` — Personal-information, cross-boundary, and the explicit employee-contact-detail / profile-workaround prohibition.
- `workspace:/docs/employees.md` — Separation of employee and customer accounts.
- `bin_help:id.help.txt` — Actor output shape for ownership/disclosure branching.
- `sql_table:staff` — The staff record carries the private email/profile contact fields and operational title/role/store_id.
