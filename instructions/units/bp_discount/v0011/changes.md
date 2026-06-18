# bp_discount v0011

- mode: `manual_refactor`
- created_by: `human`
- created_at: `2026-06-18T00:26:47+00:00`
- parent: `v0010`

## Rationale

Refactor refs from a flat scratchpad list into typed Evidence ledger roles. refs.md owns the shared model and safety projection; topic BPs classify their domain evidence; submission_terminal checks the completed ledger before submit.

## Rollback

Retire this version to fall back to v0010, or issue a new manual_refactor version with adjusted ledger wording.

## Dependencies
- `workspace:/docs/discounts.md` — Full gate set: percent tiers, reason-code enum, retired-phrase and campaign-label anti-patterns, the line-eligibility bridge into /docs/checkout.md, and the manager-store-match gate.
- `workspace:/docs/checkout.md` — Line-eligibility gate text (quantity <= available_today, missing inventory row = unsupported) the discount policy applies at gate 8.
- `bin_help:discount.help.txt` — Tool signature /bin/discount <basket_id> <percent> <reason_code> <issuer_id> and the 'no policy checks' disclaimer.
- `sql_table:shopping_baskets` — Basket ownership, store, basket_status, discount columns, and line shape used by the gate set.
- `sql_table:shopping_basket_items` — requested_quantity used for subtotal and checkoutability checks when the line projection is queried directly.
- `sql_table:product_variants` — price_cents and canonical catalogue record_path used for subtotal and evidence.
- `sql_table:store_inventory` — available_today_quantity line-eligibility gate.
- `sql_table:stores` — Store record_path and manager-store scope evidence.
- `sql_table:employee_accounts` — Actor/store/role context (store_id) when employee records are consulted for the manager-store match.
