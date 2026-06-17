# bp_refs v0006

- mode: `failure_fix`
- created_by: `human`
- created_at: `2026-05-29T00:51:51+00:00`
- parent: `v0005`

## Rationale

Clarifies the `/docs/checkout.md` tie-breaker for applied policy refs. `bp_discount` v0010 treats checkout eligibility used during target resolution (for example selecting a checkoutable basket before a later discount gate denies) as an application of `/docs/checkout.md`. `bp_refs` v0005 still said to include checkout.md only when the topic BP evaluated its gate, which could be read too narrowly as only the line-eligibility gate.

v0006 keeps the general applied-policy rule and clarifies that applying checkout rules includes both evaluating the line gate and using checkout eligibility to resolve the target record. This avoids conflict with topic BPs without adding a t26-specific ref rule.

## Rollback

Revert to v0005 by creating a new version from v0005 content if blind reruns show over-citation of `/docs/checkout.md` where checkout rules were not actually used to resolve a target or evaluate a gate.

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
