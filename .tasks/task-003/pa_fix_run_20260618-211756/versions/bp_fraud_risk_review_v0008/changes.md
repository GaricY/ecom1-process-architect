# bp_fraud_risk_review v0008

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-18T18:33:04+00:00`
- parent: `v0007`

## Rationale

Owning layer: domain_policy/topic_evidence in the fraud topic BP (how the impossible-observed-travel family defines its cited cluster). The Executor copied the example travel literals (`observed_l1 > 2.0 AND minutes BETWEEN 0 AND 15`) verbatim and used them as a hard gate, then cited only the records that were the destination of an individually-flagged hop. For the one multi-hop chain in scope (cust_082, night of 2021-05-26) this dropped two genuine chain members: a hop with displacement just under 2.0 over ~0.9 min (the fastest, most-impossible hop) and a hop with a large displacement ~5 min past the 15-min window. That under-capture is the ~10% of fraud EUR the grader flagged as missing. Fix: redefine impossible travel as a speed criterion (observed displacement / elapsed time exceeding plausible travel), explicitly flag that the distance/time literals are illustrative not the gate, and require expanding a fired hop to the full chain of consecutive impossible-speed hops for that actor — mirroring the burst family's existing 'expand to all in-window records' rule, which the travel family lacked. Reinforced with a coverage-check self-audit line and one anti-pattern. This is a single focused edit to the family that under-specified its cohort, not a stack on top of a prior PA rule (recent versions v0005-v0007 were schema-rename and refs-ledger refactors, not travel-threshold changes), so nothing is being re-litigated.

## Rollback

Create a new version from v0007 content if the speed-based / chain-expansion travel rule over-captures (e.g. pulls legitimate same-night long-gap payments into a chain), restoring the fixed-literal travel description.

## Dependencies
- `workspace:/docs/payments/3ds.md` — Workflow-state invariant family in this BP checks paid rows against legitimate 3DS transitions; wording goes stale if the 3DS policy changes.
- `sql_table:payment_transactions` — Primary risk record; the edited travel rule computes observed speed from observed_latitude/observed_longitude and payment_created_at, so a schema change to these columns invalidates the rule.
- `sql_table:customer_accounts` — Home-coordinate context (home_latitude/home_longitude) used to separate remote shopping from observed-location fraud in the soft/hard discriminator.
- `sql_table:stores` — Store branch location axis the BP warns against using for the travel check; rule references it to keep observed-to-observed separate from store distance.
- `sql_table:shopping_baskets` — Basket/customer/store joins and archive context used by the record/table invariant family.
- `sql_table:shopping_basket_items` — Basket resource lines (requested_quantity) for the quantity/resource reconciliation invariant.
- `sql_table:payment_transaction_items` — Line-level reconciliation (purchased_quantity, item_unit_price_cents) for the amount-vs-lines invariant family.
- `sql_table:product_variants` — Catalogue price joins for amount/line checks.
- `sql_table:store_inventory` — Reserve/availability arithmetic and store/SKU resource axis cited in the general risk primitives.
- `sql_table:return_requests` — Return/payment/basket/customer workflow joins cited in the general risk primitives.
- `workspace:/proc/payments/README.md` — Defines observed_lat/observed_lon as checkout-time risk-log coordinates (not address); the speed-based travel rule depends on that semantics being accurate.
- `workspace:/proc/customers/README.md` — Coarse customer home-area coordinate semantics used to keep home distance a soft signal.
- `workspace:/proc/stores/README.md` — Store branch coordinate semantics referenced when distinguishing store-distance from observed travel.
