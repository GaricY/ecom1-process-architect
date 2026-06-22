# bp_identity_and_auth v0005

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-30T09:37:50+00:00`
- parent: `v0004`

## Rationale

security.md was reformatted and gained an explicit employee-contact non-disclosure line; the customer record family (/proc/customers) no longer exists (customer_id is an external id); /proc/employees/README.md was removed so the roster note is re-derived from /proc/staff + staff_roles + the schema role enum; proc families renamed (carts, payment-ledger, return-workflows, staff); /bin/sql is down so record reads use /bin/jq|cat.

## Rollback

Restore v0004 content (re-add /proc/customers and /proc/employees/README.md roster bundles, old proc family names, drop the employee-contact disclosure note).

## Dependencies
- `workspace:/docs/security.md` — Sole authority for identity, ownership, cross-boundary rule, capability-vs-boundary distinction, employee-contact non-disclosure, and the legacy phrase glossary.
- `bin_help:id.help.txt` — Defines the /bin/id output (user, roles) used to branch on actor type.
- `sql_table:staff` — Employee record: roles and assigned store_id.
- `sql_table:staff_roles` — Per-employee role assignments used for capability gates.
