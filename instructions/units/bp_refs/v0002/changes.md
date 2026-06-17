# bp_refs v0002

- mode: `failure_fix`
- created_by: `codex`
- created_at: `2026-05-26T15:30:16+00:00`
- parent: `v0001`

## Rationale

Add the pre-submit message hygiene check back to the universal refs/submission path while keeping citation decisions in bp_refs.

## Rollback

Create a new version from v0001 if the message hygiene check conflicts with a domain-specific answer format.

## Dependencies
- `workspace:/docs/security.md` — Authority for cross-boundary and personal-information citation boundaries.
- `bin_help:id.help.txt` — Actor shape used by customer/employee/guest citation branches.
- `sql_table:baskets` — Basket ownership, status, store pointer, and canonical path shape refs decisions.
- `sql_table:payments` — Payment ownership, basket/store pointers, status, and canonical path shape refs decisions.
- `sql_table:returns` — Return ownership, basket/payment pointers, status, and canonical path shape refs decisions.
- `sql_table:customers` — Customer profile/contact fields determine private citation boundaries.
- `sql_table:employees` — Employee roster/contact fields and assigned-store scope determine private vs operational refs.
- `sql_table:stores` — Public store path and location fields are required public-record refs.
- `sql_table:products` — Public catalogue path and SKU fields are required public-record refs.
