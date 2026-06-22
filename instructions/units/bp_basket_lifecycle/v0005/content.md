# Basket Lifecycle

## When this process applies

Any request that reads, names, or asks about a `/proc/carts/<customer_id>/<id>.json` record. Trigger phrases: "my basket", "the last basket", "my latest active basket", a literal basket/cart id, "basket status", or as a preliminary read inside [checkout](checkout.md), [discount](discount.md), [payments_3ds_recovery](payments_3ds_recovery.md), and [returns](returns.md). This BP is the **state registry** for reads; mutation lives in the sibling BPs.

## Inputs

- Live workspace paths:
  - `/proc/carts/<customer_id>/<id>.json` — the basket (cart) record being read.
  - `/proc/payment-ledger/<customer_id>/<id>.json` — for archived-payment context where an older payment can outlive its basket file.
- Tools: `/bin/jq` / `/bin/cat` (`ws.read`, `ws.list`) over `/proc/carts`. `/bin/sql` is unavailable — see [os_tooling_incidents](os_tooling_incidents.md). Record shapes are in `bin-help/sqlite_schema.txt`.

**Record shape (from `bin-help/sqlite_schema.txt`, `carts` / `cart_lines`).** A cart JSON carries `id`, `customer_id`, `store_id`, `status`, `created_at`, an optional `discount` object (`percent`, `reason_code`, `issuer_id`), and a `lines[]` array of `{ "sku", "quantity" }`. `record_path` is `/proc/carts/<customer_id>/<id>.json`.

## Process

1. Apply [identity_and_auth](identity_and_auth.md). For a customer actor, verify `cart.customer_id == /bin/id user` before reading or citing the file; a foreign basket → `OUTCOME_DENIED_SECURITY` and the path stays out of refs.
2. Read the record. The cart carries `id`, `customer_id`, `store_id`, `status`, `created_at`, an optional `discount` object, and `lines[]` (`sku`, `quantity`). **Basket lines carry no availability flag** — inventory must be re-checked every time. Same-day availability is computed against branch inventory (`/proc/locations`); see [availability](availability.md) and [checkout](checkout.md).
3. Determine state. From the `carts.status` enum the statuses are `active`, `abandoned`, `checked_out`:
   - `active` → eligible target for a basket item edit and [checkout](checkout.md), and [discount](discount.md). May still fail downstream gates.
   - `abandoned` → not a live working basket; do not edit, check out, or discount it.
   - `checked_out` → historical order. Re-running `/bin/checkout` on it is forbidden. Eligible target for [payments_3ds_recovery](payments_3ds_recovery.md) (via the linked payment) and [returns](returns.md).
4. For "the last basket" / "my latest active basket" wording, sort by `created_at` descending within the actor's own carts (customer actor) or within the request-named scope (employee actor). `/docs/checkout.md`: use the active basket with the latest `created_at`; this resolves "my basket" without clarification even when several active baskets exist. `created_at` is generated world time; compare against `/bin/date` only if recency matters — see [date_and_time](date_and_time.md).
5. For "does this basket have a discount?" — check whether the `discount` object is present. Presence blocks new discount issuance — see [discount](discount.md).
6. Archived-payment context: a payment under `/proc/payment-ledger` may carry `archived: true` and may omit `order_id` / `basket_id`; such carts may have aged out of `/proc/carts`. If a missing basket id came from a linked payment/return, check the payment `archived` flag before treating the missing file as an inconsistent basket.

## Outcomes

- This BP does not produce a final outcome on its own. It is a building block; the sibling BP that invoked it produces the outcome.
- If a basket id named in the request does not exist at all, the sibling BP should submit `OUTCOME_NONE_UNSUPPORTED` (basket missing) or `OUTCOME_NONE_CLARIFICATION` (ambiguous which basket). Exception: when the id is linked from an archived payment, the payment record may be the surviving order evidence rather than a broken basket.

## Refs to set in scratchpad

- `/proc/carts/<customer_id>/<id>.json` — only if ownership passed (customer actor) or it is the action target (employee actor). See [refs](refs.md).
- For ambiguous baskets in `OUTCOME_NONE_CLARIFICATION`, cite each candidate cart path the actor actually owns.

## Anti-patterns

- Citing a foreign customer's cart path in refs because the request quoted the id (personal-data leak — see [refs](refs.md)).
- Treating store-floor or culture slang as a basket state. The only states are `active`, `abandoned`, `checked_out`.
- Assuming a basket line is available because the basket exists — lines have no availability flag. Re-check branch inventory for `(store_id, sku)`.
- Treating `created_at` from a record as "now" — recency comparisons use `/bin/date`. See [date_and_time](date_and_time.md).
- Trying `/bin/sql` to list baskets — it is down; list/read `/proc/carts` JSON via `/bin/jq` / `/bin/cat`.

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived.

- `bin-help/sqlite_schema.txt` — `carts` / `cart_lines` record shape, the `active`/`abandoned`/`checked_out` status enum, the `discount` object semantics, and the `record_path` convention (replaces the removed `/proc/baskets/README.md`).
- `bin-help/jq.help.txt`, `bin-help/cat.help.txt` — the JSON read tools used for cart lookups now that `/bin/sql` is unavailable.
- `sql_table carts` — basket id, status, store pointer, created-at, discount object.
- `sql_table cart_lines` — basket line shape (`sku`, `quantity`).
- `sql_table payment_ledger` — `archived` flag and cold-storage semantics where a payment outlives its cart (replaces the removed `/proc/payments/README.md`).
