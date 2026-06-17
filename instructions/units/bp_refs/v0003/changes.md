# bp_refs v0003

- mode: `failure_fix`
- created_by: `codex`
- created_at: `2026-05-26T22:06:11+00:00`
- parent: `v0002`

## Rationale

Clarify refs for non-pure availability answers: a public product identified in the final answer still needs its canonical products.path even if it failed a stock predicate; pure availability answer sets keep the unavailable-product exclusion.

## Rollback

Create a new version from v0002 if this distinction causes pure availability answers to cite products that were only considered and not identified in the response.

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
