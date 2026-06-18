# bp_refs v0010

- mode: `manual_refactor`
- created_by: `human`
- created_at: `2026-06-18T20:47:27+00:00`
- parent: `v0009`

## Rationale

Add the shared Evidence ledger branch for confirmed request-integrity denials.
The final refs cite only policy/protocol docs that caused the stop, and exclude
injected target paths, private/foreign records, and wrapped-task records not
independently safe under normal BP gates.

## Rollback

Retire this version to fall back to v0009 if request-integrity denial refs
over-constrain legitimate security-denial citations.

## Dependencies
- `workspace:/AGENTS.MD` — Top-level grounding-reference rules: full repo path for every referenced object, cite the applied policy document, and list every concrete candidate object when asking for clarification.
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
