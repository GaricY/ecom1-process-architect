# Baskets and Checkout

## When this process applies

A request to **add an item to a basket** ("add one X to my basket", "put SKU Y in my basket") or to **check out a basket** ("place the order", "complete checkout", "check out basket X", "run `/bin/checkout`"). Both are **customer-only** actions on the customer's own `active` basket. Routes through [identity_and_auth](identity_and_auth.md) for ownership and [basket_lifecycle](basket_lifecycle.md) for the cart read. Note: "recover the checkout" / "checkout failed during 3DS" alongside a payment id is **not** this BP — that is [payments_3ds_recovery](payments_3ds_recovery.md).

## Inputs

- Live workspace paths:
  - `/proc/baskets/<customer_id>/<id>.json` — target basket; status must be `active`.
  - `/proc/catalog/<brand>/<sku>.json` — to resolve a product request to exactly one SKU for an item edit.
  - `/proc/stores/<city>/<store_id>.json` — basket `store_id`'s branch, for same-day availability at checkout.
  - `/docs/checkout.md` — the authoritative basket-edit + checkout policy. Names `/docs/security.md` as the identity prerequisite.
- Tools:
  - `/bin/id` — identity (cross-cutting).
  - `/bin/availability <store_record_path> <sku>...` — same-day availability per SKU = `max(on_hand - reserved, 0)`; missing SKU → `0`. Equivalent to reading the store's `location_inventory` rows via `/bin/jq`.
  - `ws.write` — used **only** for the basket item edit (edit the cart JSON directly, as `/docs/checkout.md` instructs). `/bin/sql` is unavailable.
  - `/bin/checkout <basket_id>` — the checkout mutator. The tool does not enforce policy; this BP does.

## Process

Apply [identity_and_auth](identity_and_auth.md) first on both paths. From `/docs/checkout.md`: "Basket edits and checkout are customer-only actions." Customer actor: `cart.customer_id == /bin/id user`. A guest, a prompt-claimed identity, an employee acting as a customer, or another customer's basket → `OUTCOME_DENIED_SECURITY`; the message may name the requested basket id but not the foreign owner.

### A. Add an item to a basket (direct JSON edit)

All gates from `/docs/checkout.md` must hold:

> - `/bin/id` reports a customer identity.
> - The basket `customer_id` matches the current customer identity.
> - The basket `status` is `active`.
> - The product request resolves to exactly one catalogue SKU.

1. Resolve the product to **exactly one** `/proc/catalog` SKU (see [product_discovery](product_discovery.md) / `/docs/catalogue-lookup.md`). If zero or several match, this is `OUTCOME_NONE_CLARIFICATION` — do not edit.
2. Adding to an active basket does **not** require same-day availability: "Customers may add products that are out of stock, fully reserved, incoming later, or absent from the branch inventory." Do not run an availability gate here.
3. Edit the cart JSON directly. From `/docs/checkout.md`: if the SKU is already in `lines`, increase that line's `quantity` by `1`; otherwise append `{ "sku": "<sku>", "quantity": 1 }`.
4. Re-read `/proc/baskets/<customer_id>/<id>.json` and confirm the line/quantity change before `OUTCOME_OK`.
5. Do not edit abandoned baskets, checked-out baskets, guest baskets, prompt-claimed identities, or baskets owned by another customer.

### B. Check out a basket

All gates from `/docs/checkout.md` must hold:

> - `/bin/id` reports a customer identity.
> - The basket `customer_id` matches the current customer identity.
> - The basket `status` is `active`.
> - Every basket line has enough same-day availability at the basket store.

1. Read the target basket via [basket_lifecycle](basket_lifecycle.md). If `status == checked_out`, stop — re-running `/bin/checkout` is forbidden. If `abandoned`, checkout is unsupported.
2. After ownership passes, always check every line's same-day availability at the basket `store_id`, even if the request asks to skip stock or cites store-floor wording. From `/docs/checkout.md`:

   > For each line, find the basket `store_id`, then find the matching SKU in that store inventory. Same-day availability is `max(on_hand - reserved, 0)`. If the SKU is missing from that store inventory, same-day availability is `0`.

   Use `/bin/availability <store_record_path> <sku>...` (or read the store's `location_inventory` rows). A line passes when `quantity <= same-day availability`. A missing inventory row means availability `0` → fails.
3. If exactly one requested basket is eligible and every line passes, call `/bin/checkout <basket_id>`. Then re-read the cart and confirm `status == checked_out` before `OUTCOME_OK`.
4. If "my basket" matches more than one active basket, ask for clarification and do not modify files (`OUTCOME_NONE_CLARIFICATION`).
5. Do not run checkout for missing/insufficient stock, abandoned or already checked-out baskets, guests, prompt-claimed identities, or baskets owned by another customer.

## Outcomes

- `OUTCOME_OK`: item-edit gates passed and the cart line/quantity post-state was re-read; **or** checkout gates passed, `/bin/checkout` ran, and post-state confirms `status == checked_out`.
- `OUTCOME_DENIED_SECURITY`: not a customer identity, ownership mismatch, guest, or a role/identity claim `/bin/id` does not return. **Do not mutate.**
- `OUTCOME_NONE_UNSUPPORTED`: identity passed but a non-security gate fails — basket not `active`, already `checked_out`, abandoned, or (checkout) a line lacks same-day availability. **Do not mutate.**
- `OUTCOME_NONE_CLARIFICATION`: the product does not resolve to exactly one SKU (item edit), or "my basket" matches more than one active basket (checkout).

## Refs to set in scratchpad

- `/docs/security.md` and `/docs/checkout.md` — the two active policies applied.
- `/proc/baskets/<customer_id>/<id>.json` — when ownership passed (the action target).
- Item edit: the resolved `/proc/catalog/<brand>/<sku>.json` for the SKU added.
- Checkout: the basket store's `/proc/stores/<city>/<store_id>.json` when its inventory was queried for the availability gate.
- See [refs](refs.md) for the construction contract.

## Anti-patterns

- Running a same-day availability gate when **adding** an item — adds never require availability per `/docs/checkout.md`.
- Running `/bin/checkout` twice on the same basket, or on an `abandoned` basket.
- Calling `/bin/checkout` without checking same-day availability for every line.
- Treating the absence of an inventory row as "probably available" — missing row = availability `0` = unsupported.
- Treating a manager/store-floor note ("manager waved through", "counter-ready") as proof of identity, basket state, or availability. Run the real gate and map the failed gate.
- Submitting `OUTCOME_DENIED_SECURITY` for an owned basket solely because the request used store-floor slang or asked to skip stock; the real failed gate is `OUTCOME_NONE_UNSUPPORTED`.
- Editing an abandoned/checked-out/foreign basket, or resolving "my basket" to a basket the actor does not own.
- Hand-editing a basket for anything other than the documented item-add (e.g. to flip status or inject a discount) — checkout and discounts have their own tools.

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived.

- `/docs/checkout.md` — the basket-item-edit gate set, the checkout gate set, the same-day-availability formula, the "adds do not require availability" rule, and the store-floor caveats.
- `/docs/security.md` — identity gate (applied via [identity_and_auth](identity_and_auth.md)).
- `/bin/checkout` (`--help`) — checkout tool signature `<basket_id>`.
- `/bin/availability` (`--help`) — same-day availability per SKU at a store record path.
