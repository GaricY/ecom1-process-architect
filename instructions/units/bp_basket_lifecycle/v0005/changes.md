# bp_basket_lifecycle v0005

- mode: `manual_refactor`
- created_by: `human`
- created_at: `2026-06-18T00:26:47+00:00`
- parent: `v0004`

## Rationale

Refactor refs from a flat scratchpad list into typed Evidence ledger roles. refs.md owns the shared model and safety projection; topic BPs classify their domain evidence; submission_terminal checks the completed ledger before submit.

## Rollback

Retire this version to fall back to v0004, or issue a new manual_refactor version with adjusted ledger wording.

## Dependencies
- `workspace:/proc/baskets/README.md` — Record shape, status semantics, discount object semantics, and the 'no availability flag' rule.
- `sql_table:shopping_baskets` — Basket id, basket_status, store pointer, basket_created_at, and discount columns read by this registry.
- `sql_table:shopping_basket_items` — Basket line shape (line_number, product_sku, requested_quantity) used in reconciliation.
- `workspace:/proc/payments/README.md` — Archived-payment semantics: older payments can carry line snapshots after basket files age out.
