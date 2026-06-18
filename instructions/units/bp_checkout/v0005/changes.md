# bp_checkout v0005

- mode: `manual_refactor`
- created_by: `human`
- created_at: `2026-06-18T00:26:47+00:00`
- parent: `v0004`

## Rationale

Refactor refs from a flat scratchpad list into typed Evidence ledger roles. refs.md owns the shared model and safety projection; topic BPs classify their domain evidence; submission_terminal checks the completed ledger before submit.

## Rollback

Retire this version to fall back to v0004, or issue a new manual_refactor version with adjusted ledger wording.

## Dependencies
- `workspace:/docs/checkout.md` — Gate set, source order, and Store Desk Checkout Vocabulary anti-patterns; the verbatim line-eligibility quote.
- `workspace:/docs/security.md` — Identity gate applied via identity_and_auth before the stock check.
- `bin_help:checkout.help.txt` — Tool signature /bin/checkout <basket_id>.
- `sql_table:shopping_baskets` — Ownership (customer_id), basket_status, store pointer, and canonical basket shape.
- `sql_table:shopping_basket_items` — Basket line requested_quantity when queried directly.
- `sql_table:store_inventory` — available_today_quantity and missing-row checkout gates, keyed by (store_id, product_sku).
