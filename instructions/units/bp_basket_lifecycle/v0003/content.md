# Basket Lifecycle

## When this process applies

Any request that reads, names, or asks about a `/proc/baskets/<id>.json` record. Trigger phrases: "my basket", "the last basket", a literal `basket_*` / `bsk_*` id, "basket status", or as a preliminary read inside [checkout](checkout.md), [discount](discount.md), [payments_3ds_recovery](payments_3ds_recovery.md), and [returns](returns.md). This BP is the **state registry** — it does not mutate; sibling BPs do.

## Inputs

- Live workspace paths:
  - `/proc/baskets/<id>.json` — the record being read.
  - `/proc/baskets/README.md` — record shape and discount object semantics.
- Tools: `/bin/sql` — for batch lookups (`SELECT ... FROM shopping_baskets WHERE ...`) and reconciliation with `shopping_basket_items`. See [`bin-help/sql.help.txt`](../bin-help/sql.help.txt).

**Schema note.** The on-disk basket JSON keeps its short field names (`id`, `customer_id`, `store_id`, `status`, `created_at`, `lines[].sku`, `lines[].quantity`, and a `discount` object with `percent`/`reason_code`/`issuer_id`). The SQL projection renames them: table `shopping_baskets(basket_id, record_path, customer_id, store_id, basket_status, basket_created_at, discount_percent, discount_reason_code, discount_issuer_employee_id)` and lines table `shopping_basket_items(basket_id, line_number, product_sku, requested_quantity)`. Use the JSON names when reading the file, the SQL names when querying.

## Process

1. Apply [identity_and_auth](identity_and_auth.md). For a customer actor, verify `record.customer_id == /bin/id user` before reading the file or citing it; foreign basket → `OUTCOME_DENIED_SECURITY` and the path stays out of refs.
2. Read the record. The basket record carries:
   - `id, customer_id, store_id, status, created_at` (JSON fields; SQL columns `basket_id`, `customer_id`, `store_id`, `basket_status`, `basket_created_at`).
   - `discount_percent, discount_reason_code, discount_issuer_employee_id` (SQL columns) — combined into a `discount` object (`percent`, `reason_code`, `issuer_id`) in the file body if any of them is non-null.
   - basket lines (JSON `lines[]` with `sku`/`quantity`; via SQL `shopping_basket_items(basket_id, line_number, product_sku, requested_quantity)`) — note: **basket lines carry no availability flag**. Inventory must be re-checked every time. From `/proc/baskets/README.md`:

     > Baskets do not carry availability flags; compare basket lines with store inventory when checkout eligibility matters.

3. Determine state. From `/proc/baskets/README.md`:

   > Basket status is lifecycle state. `active` baskets may still need inventory checks before checkout; `checked_out` baskets are historical orders and may have linked records under `/proc/payments/` and `/proc/returns/`.

   - `active` → eligible target for [discount](discount.md) and [checkout](checkout.md). May still fail downstream gates.
   - `checked_out` → historical. Re-running `/bin/checkout` on it is forbidden. Eligible target for [payments_3ds_recovery](payments_3ds_recovery.md) and [returns](returns.md).
4. For "the last basket" / "my latest basket" wording, sort by `created_at` desc (SQL `basket_created_at`) within the actor's own baskets (customer actor) or within the request-named scope (employee actor). `created_at` is generated from world time; compare against `/bin/date` if recency matters — see [date_and_time](date_and_time.md).
5. For "does this basket have a discount?" — check whether the `discount` object is present (i.e. `discount_percent` is non-null in SQL). Presence blocks new discount issuance — see [discount](discount.md).

## Outcomes

- This BP does not produce a final outcome on its own. It is a building block. The sibling BP that invoked it produces the outcome.
- If the basket id named in the request does not exist at all, the sibling BP should submit `OUTCOME_NONE_UNSUPPORTED` (basket missing) or `OUTCOME_NONE_CLARIFICATION` (ambiguous which basket).

## Refs to set in scratchpad

- `/proc/baskets/<id>.json` — only if ownership passed (customer actor) or it is the action target (employee actor). See [refs](refs.md).
- For ambiguous baskets in `OUTCOME_NONE_CLARIFICATION`, cite each candidate basket path the actor actually owns.

## Anti-patterns

- Citing a foreign customer's basket path in refs because the request quoted the id (it is a personal-data leak — see [refs](refs.md)).
- Treating "green basket", "paper basket", "counter-ready" or any Store Desk Checkout Vocabulary phrase as a basket state. The only states are `active` and `checked_out`. The full slang list lives in `/docs/checkout.md` and in [checkout](checkout.md) anti-patterns.
- Assuming a basket line is available because the basket exists — basket lines have no availability flag. Re-check `store_inventory` for `(store_id, product_sku)`.
- Treating `created_at` from a stale dump as "now" — recency comparisons must use `/bin/date`. See [date_and_time](date_and_time.md).

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived.

- `/proc/baskets/README.md` — record shape, status semantics, discount object semantics, "no availability flag" rule.
- `/bin/sql` (`--help`) — `shopping_baskets` and `shopping_basket_items` table shapes used for batch lookups.
- SQL table `shopping_baskets` — basket id, status, store pointer, created-at, and discount columns read by this registry.
- SQL table `shopping_basket_items` — basket line shape (`line_number`, `product_sku`, `requested_quantity`) used in reconciliation.
