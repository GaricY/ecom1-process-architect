# bp_fraud_risk_review v0009

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-18T09:44:32+00:00`
- parent: `v0008`

## Rationale

The t48 trial scored 58.8%: the answer recovered only ~73% of the true fraud amount AND cited more than ten false-positive payments. Both defects come from how the Executor used the impossible-observed-travel family: it ran the consecutive-pair lag() detector (L1>2.0 inside 15 min) and then cited exactly the two rows that bracket each flagged jump. (1) Under-recovery: a real travel-fraud incident is a dense per-actor window where one identity appears at impossibly-separated places; rows whose neighbour transition is same-city or just outside the 15-min gate are dropped, undercounting the cohort and the EUR amount. (2) False positives: lone isolated two-event crossings on otherwise-unremarkable actors (cust_066/092/023/047/076 and a single borderline cust_072 pair) were promoted to confirmed incidents with no surrounding dense rotation and no other hard-family signal. The new v0008 (other PA) rewrote rules 14-15 to stop unioning UNCONNECTED cross-actor clusters under a single-hit brief; that is correct and I keep it verbatim. But v0008 leaves both t48 root causes untouched: t48 is a plural-incidents brief, so its cardinality reconciliation never triggers, and it never says (a) expand a confirmed travel hit to the actor's full dense window or (b) that a lone two-event crossing is soft until corroborated. I extend v0008 with exactly those two complementary, within-actor rules (rule 9 expansion + rule 13 caveat + travel/stationary shape notes + a travel-cohort-completeness coverage bullet + an isolated-crossing ledger bullet + three anti-patterns). These are orthogonal to v0008's cross-actor union/cardinality axis and were never previously tried or reverted. No task literals; dependency set is unchanged from v0008.

## Rollback

Create a new version from v0008 content if the dense-window expansion over-collects or the lone-two-event soft-demotion under-collects travel cohorts; that restores v0008's adjacent-pair travel wording while keeping its rule 14-15 connection/cardinality logic intact.

## Dependencies
- `workspace:/docs/payments/3ds.md` — Legitimate 3DS workflow-state transitions used for the payment workflow-state-invariant hard family this BP still owns.
- `sql_table:payment_transactions` — Primary risk record. The expanded travel rule reads observed_latitude/observed_longitude, payment_created_at, customer_id, and is_archived_basket_reference; a schema change to these columns would invalidate the dense-window-cluster rule.
- `sql_table:customer_accounts` — Actor identity and home_latitude/home_longitude context used to separate remote-shopping (soft) from observed-location fraud in the location rules touched by this edit.
- `sql_table:stores` — Store branch-location axis cited by the 'do not compute travel from store/target coordinates' rule that sits alongside the edited bullet.
- `sql_table:shopping_baskets` — Basket/customer/store joins and archive context for the record/table-invariant hard family; repeated-basket collisions are a cross-actor connecting signal.
- `sql_table:shopping_basket_items` — Basket resource lines (requested_quantity) for quantity/resource reconciliation invariants.
- `sql_table:payment_transaction_items` — Line-level reconciliation (purchased_quantity, item_unit_price_cents) for the amount-vs-lines invariant referenced by the BP.
- `sql_table:product_variants` — Catalogue price joins for amount/line invariant checks.
- `sql_table:store_inventory` — Reserve/availability arithmetic and store/SKU resource axis for the general risk primitives.
- `sql_table:return_requests` — Return/payment/basket/customer workflow joins for the general risk primitives.
- `workspace:/proc/payments/README.md` — Defines that observed_lat/observed_lon are checkout-time risk-log coordinates (not address) and that fingerprints are opaque — the load-bearing semantics behind the observed-travel dense-window rule and the identifier-collision connection test.
- `workspace:/proc/customers/README.md` — Coarse customer home-area coordinate semantics used to keep observed-vs-home distance a soft signal in the location rules.
- `workspace:/proc/stores/README.md` — Store branch-coordinate semantics for the payment-risk distance checks referenced by the location rules.
