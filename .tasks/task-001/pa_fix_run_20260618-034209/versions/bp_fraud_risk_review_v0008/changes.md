# bp_fraud_risk_review v0008

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-18T00:59:28+00:00`
- parent: `v0007`

## Rationale

The trial's true fraud cohort is structured as dense same-actor teleport bursts (many impossibly-far events in a tight window) plus cross-actor device-fingerprint collisions. The Executor applied the canonical 'impossible observed travel' query (observed_l1 > 2.0 within 15 min) as a HARD signal at the level of individual consecutive pairs, then unioned only the rows that crossed the band. This produced both grader complaints at once: (1) >10 false positives, because isolated two-event band crossings (one actor, one lone jump, no surrounding burst) were admitted as fraud even though the BP elsewhere calls a threshold-only band soft; and (2) ~10% of the fraud amount missed, because within real bursts the pair-only union dropped in-window events whose individual hop fell at/below the band. The BP's 'expand a hard hit to all in-window records' rule existed only for the stationary-burst family, never for the impossible-travel family, and the travel SQL presented a raw fixed threshold as the hard gate. This edit makes impossible travel hard ONLY as a connected multi-hop teleport burst (a lone isolated crossing is soft unless corroborated by another hard signal), and requires expanding a confirmed teleport burst to the actor's full in-window event set rather than only the threshold-crossing pairs. It changes no fixed numeric thresholds and adds no trial literals; it is a structural-confirmation rule that generalises to any archived-payment/risk variant.

## Rollback

Create a new version from v0007 content if the connected-burst requirement drops genuine isolated single-pair fraud or the burst-expansion over-collects in-window legitimate events.

## Dependencies
- `workspace:/docs/payments/3ds.md` — Defines the legitimate 3DS workflow-state transitions used by the workflow-state-invariant hard family this BP still scans.
- `sql_table:payment_transactions` — Primary risk record; the observed_latitude/observed_longitude, payment_created_at, customer_id and is_archived_basket_reference columns are exactly what the edited teleport-burst (observed-travel) logic reads.
- `sql_table:customer_accounts` — Supplies the home-coordinate context used to distinguish remote shopping from observed-location fraud, which underpins the soft-vs-hard discrimination in this BP.
- `sql_table:stores` — Store branch location axis; the BP explicitly forbids computing travel from store coordinates, so a store-schema change can make that distinction text stale.
- `sql_table:shopping_baskets` — Basket/customer/store join and archive context referenced by the record/table-invariant hard family.
- `sql_table:shopping_basket_items` — Basket resource lines (requested_quantity) used by the resource/quantity reconciliation invariant.
- `sql_table:payment_transaction_items` — Line-level amount reconciliation (purchased_quantity, item_unit_price_cents) for the amount-vs-lines record invariant, including archived payments' line snapshots.
- `sql_table:product_variants` — Catalogue price join used in amount/line anomaly checks.
- `sql_table:store_inventory` — Reserve/availability arithmetic and store/SKU resource axis cited as a current example primitive in this BP.
- `sql_table:return_requests` — Return/payment/basket/customer join cited as a current example primitive in this BP.
- `workspace:/proc/payments/README.md` — Defines that observed coordinates are checkout-time risk-log coordinates (not addresses) and that archived payments carry a line snapshot; this semantics is the basis for treating a lone observed jump as soft until a burst confirms it.
- `workspace:/proc/customers/README.md` — Defines coarse home-area coordinate semantics used by risk fixtures, load-bearing for the remote-shopping-vs-fraud distinction.
- `workspace:/proc/stores/README.md` — Defines store branch coordinate semantics used for distance checks, relevant to the store-vs-observed coordinate separation this BP enforces.
