# bp_privacy_and_disclosure v0004

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-30T09:37:50+00:00`
- parent: `v0003`

## Rationale

The customer_accounts table no longer exists in the live /proc projection, so the customer-contact-field model is re-derived around external customer_id identifiers; security.md added the explicit rule that customers/guests must not receive employee contact details (staff email/profile); /proc/customers/README.md was removed; employee contact data now lives in /proc/staff.

## Rollback

Restore v0003 content (re-add customer_accounts/employee_accounts SQL contact-field model and /proc/customers/README.md, drop the explicit employee-contact rule emphasis).

## Dependencies
- `workspace:/docs/security.md` — Personal-information cross-boundary rule and the employee-contact non-disclosure rule.
- `bin_help:id.help.txt` — Actor output shape for ownership/disclosure branching.
- `sql_table:staff` — Employee contact/profile fields (email, display_name, title) and assigned store_id that are private by default; replaces the removed customer_accounts table.
