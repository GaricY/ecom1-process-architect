# bp_fraud_risk_review v0008

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-18T09:31:11+00:00`
- parent: `v0007`

## Rationale

The brief asserted a cardinality ('one hit is present in the archived payments'), but the Executor unioned one genuinely evidence-connected campaign (cust_068 stationary single-actor burst) with impossible-travel flags on six unrelated customers that shared no actor and no exact identifier (its own sweep showed cross-actor PMF/DFP sharing = 1, i.e. none) and a different MO. That over-inclusion produced false positives and a 91.4% FAIL. The cause is rule 14, which v0003 broadened from v0002's 'union sub-clusters that share a verified hard signature with the incident' to 'union of every hard-supported cluster in scope', plus rule 15's 'different date/MO is not enough to exclude a cluster' - together they force unioning unconnected clusters even under a single-hit brief. The fix restores the connection qualifier (so v0003's real anti-under-inclusion behaviour is preserved: sub-clusters of the SAME evidence-connected incident are still unioned) and adds explicit cardinality reconciliation: when the brief asserts one hit and the hard clusters are NOT evidence-connected (different actors, no shared identifier), treat them as competing candidates, select the single best-corroborated campaign, and route the rest to considered_not_cited (clarification only when genuinely tied). Connection is defined via the cross-actor identifier-collision result already produced by the mandatory sweep, so no new query machinery is added.

## Rollback

Create a new version from v0007 content if this re-introduces under-inclusion (e.g. dropping a real evidence-connected sub-cluster); v0007 unconditionally unions every hard cluster in scope.

## Dependencies
- `workspace:/docs/payments/3ds.md` — Legitimate 3DS workflow-state transitions used for the payment workflow-state invariant hard family referenced by the sweep.
- `sql_table:payment_transactions` — Primary risk record. The connection/cardinality rule keys on its actor (customer_id) and exact identifiers (payment_method_fingerprint, device_fingerprint) plus observed coordinates, payment_created_at, and is_archived_basket_reference.
- `sql_table:customer_accounts` — Customer identity (actor axis) and home_latitude/home_longitude context for distinguishing remote shopping from observed-location fraud; the evidence-connection test compares actors.
- `sql_table:stores` — Joined store location axis for geo anomaly checks in the travel/burst query shapes.
- `sql_table:shopping_baskets` — Basket/customer/store joins and archive context; repeated-basket collisions are one of the cross-actor connecting signals.
- `sql_table:shopping_basket_items` — Basket resource lines (requested_quantity) for quantity/resource reconciliation in record/table invariants.
- `sql_table:payment_transaction_items` — Line-level reconciliation (purchased_quantity, item_unit_price_cents) for amount-vs-lines hard checks.
- `sql_table:product_variants` — Catalogue price joins for amount/line checks.
- `sql_table:store_inventory` — Reserve/availability arithmetic and store/SKU resource axis for the General Risk Primitives.
- `sql_table:return_requests` — Return/payment/basket/customer workflow joins for broader risk invariants.
- `workspace:/proc/payments/README.md` — Archived-payment semantics, observed-coordinate meaning, and opaque fingerprint semantics underpinning the travel/burst signals and the identifier-collision connection test.
- `workspace:/proc/customers/README.md` — Coarse customer home-area coordinate semantics used by risk fixtures, distinguishing home context from observed-location fraud.
- `workspace:/proc/stores/README.md` — Store branch coordinate semantics for payment-risk/distance checks.
