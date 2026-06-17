# bp_checkout v0003

- mode: `failure_fix`
- created_by: `codex`
- created_at: `2026-05-26T15:30:16+00:00`
- parent: `v0002`

## Rationale

Resolve the checkout outcome contradiction: informal override wording is ignored and does not itself cause DENIED_SECURITY; after ownership passes, real stock/status gates determine unsupported outcomes.

## Rollback

Create a new version from v0002 if removing override-language as a DENIED_SECURITY trigger weakens true identity/role denials.

## Dependencies
- `workspace:/docs/checkout.md` — Checkout gate set, source order, and vocabulary anti-patterns.
- `workspace:/docs/security.md` — Identity gate applied via identity_and_auth.
- `bin_help:checkout.help.txt` — Checkout tool signature.
- `sql_table:baskets` — Basket ownership, status, store pointer, and canonical shape.
- `sql_table:basket_lines` — Basket line quantities when queried directly.
- `sql_table:inventory` — available_today and missing-row checkout gates.
