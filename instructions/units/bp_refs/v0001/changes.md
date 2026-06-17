# bp_refs v0001

- mode: `initial_migration`
- created_by: `codex`
- created_at: `2026-05-26T08:22:43+00:00`

## Rationale

Extract citation safety from bp_refs_and_submission into a focused refs BP. It keeps actor/ownership citation branching, public-record sweep, topic-doc routing, and discovery answer/ref parity while delegating terminal submission and fraud search to separate units.

## Rollback

Remove this unit from registry and restore bp_refs_and_submission if split citation routing drops required refs or over-cites private records.

## Dependencies
- `workspace:/docs/security.md` — Authority for cross-boundary and personal-information citation boundaries.
- `bin_help:id.help.txt` — Actor shape used by customer/employee/guest citation branches.
- `sql_table:baskets` — Basket ownership, status, store pointer, and canonical path shape refs decisions.
- `sql_table:payments` — Payment ownership, basket/store pointers, status, and canonical path shape refs decisions.
- `sql_table:returns` — Return ownership, basket/payment pointers, status, and canonical path shape refs decisions.
- `sql_table:customers` — Customer profile/contact fields determine private citation boundaries.
- `sql_table:employees` — Employee roster/contact/store fields determine employee private vs operational refs.
- `sql_table:stores` — Public store path and location fields are required public-record refs.
- `sql_table:products` — Public catalogue path and SKU fields are required public-record refs.
