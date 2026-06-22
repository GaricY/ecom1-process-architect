# bp_identity_and_auth v0008

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-22T00:02:07+00:00`
- parent: `v0007`

## Rationale

Proc families renamed (carts/payment-ledger/return-workflows) and there is no /proc/customers family — a customer is only the /bin/id user matched on customer_id. The /proc/employees/README roster was removed; roles now come from /bin/id and /proc/staff.roles[]. Added the /docs/employees.md rule: an employee identity on a customer-only action is OUTCOME_NONE_UNSUPPORTED (not a security denial). security.md is surgically updated (employee-contact privacy; account-recovery rule removed).

## Rollback

Restore bp_identity_and_auth v0007 content and its old /proc/employees/README + customer-record dependencies.

## Dependencies
- `workspace:/docs/security.md` — Sole authority for identity, ownership, cross-boundary, employee-contact privacy, and the legacy phrase glossary.
- `workspace:/docs/employees.md` — Employee accounts cannot perform customer operations -> the actor-kind unsupported branch.
- `bin_help:id.help.txt` — Defines the /bin/id user/roles output shape this BP branches on.
- `sql_table:staff` — Employee roles[], title, and assigned store_id used for employee classification; replaces the removed /proc/employees/README.
