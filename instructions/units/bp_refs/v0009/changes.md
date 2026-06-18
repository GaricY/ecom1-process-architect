# bp_refs v0009

- mode: `failure_fix`
- created_by: `human`
- created_at: `2026-06-18T08:01:43+00:00`
- parent: `v0008`

## Rationale

Completes the shared Evidence ledger model: request_named_inputs remains mandatory even when a topic BP omits it, and authorized safe gate records cannot be weakened into optional refs. Injection/message-safety behavior is deliberately left out for a separate task.

## Rollback

Create a new version from the parent content if this refactor-completion wording over-constrains executor behavior.

## Dependencies
- `workspace:/docs/security.md` — Authority for cross-boundary and personal-information citation boundaries.
- `bin_help:id.help.txt` — Actor output shape used for customer/employee/guest citation branches.
- `sql_table:shopping_baskets` — Basket ownership, store pointer, status, and canonical record_path for basket refs.
- `sql_table:payment_transactions` — Payment ownership, basket/store pointers, status, and canonical record_path for payment refs.
- `sql_table:return_requests` — Return ownership, basket/payment pointers, status, and canonical record_path for return refs.
- `sql_table:customer_accounts` — Customer identity and contact fields that are private by default.
- `sql_table:employee_accounts` — Employee roster/contact fields and assigned-store scope determine private vs operational refs.
- `sql_table:stores` — Public store record_path and location fields are required public-record refs.
- `sql_table:product_variants` — Public catalogue record_path and SKU fields are required public-record refs.
- `workspace:/proc/README.md` — Source-of-truth manifest for /proc record families and live path roots.
