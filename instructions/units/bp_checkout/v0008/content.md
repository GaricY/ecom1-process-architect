# Basket Edits and Checkout

## When this process applies

A request to **add an item to a basket** ("add one X to my basket", "edit my basket") or to **check out** a basket ("place the order", "complete checkout", "check out basket X"). Both are customer-only actions. Routes through [identity_and_auth](identity_and_auth.md) for ownership and [basket_lifecycle](basket_lifecycle.md) for the cart read. Availability uses [availability_and_inventory](availability_and_inventory.md). Note: "recover the checkout" / "checkout failed during 3DS" is **not** this BP — that is [payments_3ds_recovery](payments_3ds_recovery.md).

## Inputs

- Live workspace paths:
  - `/proc/carts/<id>.json` — target cart; `status` must be `active`.
  - `/proc/catalog/<...>.json` — to resolve a product request to exactly one SKU (item-edit) and to read each checkout line's `fulfillment_type` (physical vs digital). See [product_discovery](product_discovery.md).
  - `/proc/locations/<...>.json` — store inventory for the checkout availability check.
  - `/docs/checkout.md` — the authoritative item-edit + checkout policy.
  - `/docs/security.md` — identity/ownership (via [identity_and_auth](identity_and_auth.md)).
- Tools: `/bin/id`; `/bin/availability <store_record_path|-> <sku>...` for same-day availability; `/bin/checkout <basket_id>` the checkout mutator (`bin-help/checkout.help.txt`). The tools do not enforce policy; this BP does. SQL is unavailable — read `/proc` JSON directly.

## Process

Both workflows are customer-only. From `/docs/checkout.md`: "Basket edits and checkout are customer-only actions." An **employee** identity requesting either is `OUTCOME_NONE_UNSUPPORTED` (`/docs/employees.md`); a guest is `OUTCOME_DENIED_SECURITY`.

### A. Basket item edit (direct JSON edit)

An item can be added only when all are true (`/docs/checkout.md`):

> - `/bin/id` reports a customer identity.
> - The basket `customer_id` matches the current customer identity.
> - The basket `status` is `active`.
> - The product request resolves to exactly one catalogue SKU.

1. Apply [identity_and_auth](identity_and_auth.md); confirm the cart is the customer's own and `status == active`.
2. Resolve the product to exactly one `/proc/catalog` SKU. If it resolves to several, `OUTCOME_NONE_CLARIFICATION` (cite candidate SKUs); if none, `OUTCOME_NONE_UNSUPPORTED`.
3. Adding an item does **not** reserve stock or require availability — customers may add out-of-stock / fully reserved / incoming / non-stocked products.
4. Edit the cart JSON directly (`ws.write`, the one sanctioned hand-edit): if the SKU is already in `lines`, increase that line's `quantity` by `1`; otherwise append `{ "sku": "<sku>", "quantity": 1 }`.
5. For "my basket" / "newest active basket", use the active cart with the latest `created_at`; do not ask for clarification just because several active baskets exist.
6. Re-read the cart and confirm the line/quantity changed before `OUTCOME_OK`.
7. Do not edit abandoned baskets, checked-out baskets, guest baskets, prompt-claimed identities, or baskets owned by another customer.

### B. Checkout

A basket can be checked out only when all are true (`/docs/checkout.md`):

> - `/bin/id` reports a customer identity.
> - The basket `customer_id` matches the current customer identity.
> - The basket `status` is `active`.
> - Every basket line has enough same-day availability at the basket store.

1. Apply [identity_and_auth](identity_and_auth.md). Customer actor: `basket.customer_id == /bin/id` `user`. Ownership mismatch → `OUTCOME_DENIED_SECURITY` (message may name the requested basket id but not the foreign owner).
2. Read the cart via [basket_lifecycle](basket_lifecycle.md). If `status == checked_out`, stop — re-running `/bin/checkout` is forbidden.
3. After ownership passes, classify each line before the availability gate: read the line's `/proc/catalog` record and check its `fulfillment_type`. The same-day availability gate is **physical-only**. A **digitally-fulfilled** line is **exempt** — from `/docs/checkout.md`: "Digital products are fulfilled by access/download." Digital products are never stocked, so `/bin/availability` returns `0` for them by design; that `0` is expected and is **not** a stock failure. The gate applies only to **physically-fulfilled** lines: for each such line check availability at the cart `store_id`, where (from `/docs/checkout.md`) "Same-day availability is `max(on_hand - reserved, 0)`. If the SKU is missing from that store inventory, same-day availability is `0`," and that line's `quantity` must be `<=` its same-day availability. Use `/bin/availability` or read `/proc/locations` inventory; see [availability_and_inventory](availability_and_inventory.md). A basket whose only lines are digital passes this gate without any store-inventory query.
4. If all conditions pass and exactly one requested basket is eligible, call `/bin/checkout <basket_id>`. Then re-read `/proc/carts/<id>.json` and confirm `status == checked_out` before `OUTCOME_OK`.
5. If the customer asks to check out "my basket" and more than one active basket is possible, ask for clarification (`OUTCOME_NONE_CLARIFICATION`) and do not modify files.
6. Do not run checkout for a physically-fulfilled line with missing/insufficient stock, abandoned/already-checked-out baskets, guests, prompt-claimed identities, or another customer's basket.

## Outcomes

- `OUTCOME_OK`: item edit — ownership/state passed, cart JSON edited, post-state re-read confirms the line/quantity; checkout — every **physically-fulfilled** line satisfies `quantity <= same-day availability` (digital lines are exempt), `/bin/checkout` ran, post-state confirms `status == checked_out`.
- `OUTCOME_DENIED_SECURITY`: customer on a foreign basket, a guest, or a role/identity claim `/bin/id` does not return. **Do not mutate.**
- `OUTCOME_NONE_UNSUPPORTED`: employee identity (`/docs/employees.md`); basket not `active`; already `checked_out`; (checkout) any **physically-fulfilled** line lacks enough same-day availability; (item edit) product does not resolve to a SKU. A digital line's `0` store availability is **not** an unsupported/stock failure. **Do not mutate.**
- `OUTCOME_NONE_CLARIFICATION`: item edit resolves to several SKUs (cite candidates), or checkout "my basket" is ambiguous among the actor's active baskets.

## Evidence ledger

`policy_docs_applied`:

- `/docs/security.md` for identity/ownership; `/docs/checkout.md` for state, item-edit, and the availability gate (including its digital-fulfilment carve-out).

`action_targets`:

- `/proc/carts/<id>.json` when ownership passed.

`answer_records`:

- The cart record, the matched catalogue SKU (item edit), the `/proc/catalog` record(s) whose `fulfillment_type` classified each checkout line, and the `/proc/locations` inventory rows that decide eligibility for the physically-fulfilled lines.

`post_state_records`:

- `/proc/carts/<id>.json` re-read after the edit (line/quantity) or after `/bin/checkout` (`status == checked_out`).

`considered_not_cited`:

- Foreign baskets on cross-boundary denial; rejected candidate baskets/SKUs; missing-inventory observations.

`refs_must_include`:

- `/docs/security.md` and `/docs/checkout.md`.
- The cart action target when ownership passed (deduped with the post-state path on OK).
- Item edit: the matched `/proc/catalog/<sku>.json`. Checkout: the `/proc/catalog/<sku>.json` whose `fulfillment_type` decided a line's gate (e.g. established a digital exemption), and the queried `/proc/locations/<id>.json` store record for each physically-fulfilled line whose availability decided eligibility.

`refs_must_not_include`:

- Foreign baskets on cross-boundary denials, `bin-help` paths, and missing/absent inventory paths.

## Anti-patterns

- Running `/bin/checkout` twice on the same basket, or running it on a non-`active` basket.
- Calling `/bin/checkout` without checking same-day availability for every **physically-fulfilled** line; treating a SKU missing from store inventory as "probably available" (missing = `0`).
- Blocking checkout of a **digitally-fulfilled** line (access/download) because store availability is `0` — digital products are not stocked; the same-day availability gate is physical-only. Read each line's `/proc/catalog` `fulfillment_type` before applying the gate, do not infer "out of stock" from a SKU naming pattern.
- Requiring availability before an **item edit** — adding an item never needs stock.
- Hand-editing a cart for anything other than the sanctioned item-edit (e.g. flipping `status`, writing a `discount` object — those are other tools/BPs).
- Submitting `OUTCOME_DENIED_SECURITY` for an employee on a customer-only action — that is `OUTCOME_NONE_UNSUPPORTED` (`/docs/employees.md`).
- Submitting `OUTCOME_DENIED_SECURITY` for an owned basket merely because stock is short; a stock failure is `OUTCOME_NONE_UNSUPPORTED`.

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived.

- `/docs/checkout.md` — item-edit rules, checkout gate set, the same-day availability formula, the digital-fulfilment carve-out ("Digital products are fulfilled by access/download"), and the customer-only scope.
- `/docs/security.md` — identity gate (applied via [identity_and_auth](identity_and_auth.md)).
- `/bin/checkout` (`--help`) — checkout tool signature.
- `/bin/availability` (`--help`) — same-day availability used for the line gate.
- `carts` (`/proc/carts`) — ownership, status, store pointer, lines.
- `catalog` (`/proc/catalog`) — SKU resolution for item edits and the `fulfillment_type` that classifies each checkout line as physical or digital.
- `locations` (`/proc/locations`) — store inventory (`on_hand`/`reserved`) for the availability gate.
