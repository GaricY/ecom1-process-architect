# bp_refs v0007

- mode: `world_refresh`
- created_by: `codex`
- created_at: `2026-05-29T11:30:59+00:00`
- parent: `v0006`
- no_semantic_change: revalidated against the new dependency hashes without text edits

## Rationale

Attach /proc/README.md as the drift dependency for the proc source-of-truth manifest. Executor-visible ref behavior is unchanged because this only extends the stripped Dependencies section.

## Rollback

Revert to v0006 if proc manifest drift should be tracked solely by world_baseline instead of this unit.

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
