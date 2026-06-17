# bp_discount v0010

- mode: `failure_fix`
- created_by: `human`
- created_at: `2026-05-29T00:11:57+00:00`
- parent: `v0009`

## Rationale

t26 (discount on a checkoutable basket selected from customer baskets) fails whenever the randomized request lands on a denial branch (requested percent > policy cap, or wrong store): the agent reads and applies `/docs/checkout.md` to select the target basket, then drops it from refs because v0009 only required checkout.md when discount gate 8 (line eligibility) was reached.

v0010 keeps the fix limited to refs: checkout.md is required whenever checkout rules shaped the discount answer, either by selecting the target basket or by evaluating the line-eligibility gate. If checkout eligibility selected the target, the doc remains an applied policy even when a later non-security discount gate denies. See `.tasks/task-027/README.md`.

## Rollback

Revert to v0009 if a blind re-run shows the target-resolution rule causes over-citation of `/docs/checkout.md` on discount tasks where checkout rules were not actually applied, or otherwise regresses discount tasks.

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
