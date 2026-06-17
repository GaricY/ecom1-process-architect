# bp_refs v0004

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-28T18:31:46+00:00`
- parent: `v0003`

## Rationale

Schema rename. The canonical cite column path->record_path is load-bearing for every citation, and the identity-scoped/public table names changed: baskets->shopping_baskets, payments->payment_transactions, returns->return_requests, customers->customer_accounts, employees->employee_accounts, products->product_variants. Updated the store/product public-cite columns (stores.record_path, product_variants.record_path), the 'Identity-scoped SQL record_path column' section, and the dependency list. Conceptual /proc record-family wording and the actor/ownership branch logic are unchanged.

## Rollback

Restore bp_refs v0003 content and old sql_table dependencies (baskets, payments, returns, customers, employees, products) if the rename mapping proves wrong.

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
