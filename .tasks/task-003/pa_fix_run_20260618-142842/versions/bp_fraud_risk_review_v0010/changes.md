# bp_fraud_risk_review v0010

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-18T11:45:43+00:00`
- parent: `v0009`

## Rationale

t40 scored 34.1%: the brief ('one hit is present in the archived payments. Identify the fraudulent payment records ... cite every payment record you are marking') surfaced TWO independently hard-supported clusters - cust_068 stationary multi-store burst (12 records, ~230k cents) and cust_082 dense moving-travel burst (5 records across 5 impossibly-separated cities in ~47 min, ~510k cents). The Executor correctly classified both as hard hits, then applied v0008's single-hit reconciliation (rule 15: 'competing unconnected clusters -> select the single best-corroborated campaign, drop the rest'), used a record-count/window tiebreak ('12>5, tighter window'), and routed the hard cust_082 travel burst to considered_not_cited - recovering only ~24% of the fraud EUR. The defect is that v0008's pick-one rule was created when the dropped cluster was SOFT (lone two-event crossings, since handled by v0009's hard/soft gate at rules 9/13); applied to a genuinely HARD second incident it discards the majority of the fraud. Fix: narrow rules 14-15 so the singular 'one hit' phrasing is an existence floor, not a cap - the hard gate (rules 7-13), not the cardinality phrasing, decides membership; every cluster that independently clears the hard gate is cited (union), and a connecting signal only labels same-incident vs. independent without gating citation. The clarification fallback is reserved for mutually-exclusive readings of the SAME records. This preserves v0008/v0009's real protection (soft/lone-crossing material stays excluded by the hard gate) while stopping the loss of a separately-confirmed travel burst. No task literals; dependency set unchanged from v0009.

## Rollback

Create a new version from v0009 content if unioning all independent hard-gated clusters re-introduces false positives from decoy clusters that clear the hard gate; that restores v0008/v0009's single-hit pick-one cardinality reconciliation.

## Dependencies
- `workspace:/docs/payments/3ds.md` — Legitimate 3DS workflow-state transitions used for the payment workflow-state-invariant hard family this BP owns; one of the hard families whose clusters the edited rule 14-15 now unions.
- `sql_table:payment_transactions` — Primary risk record. The cardinality/union rule keys on its actor (customer_id), exact identifiers (payment_method_fingerprint, device_fingerprint), observed_latitude/observed_longitude, payment_created_at, and is_archived_basket_reference; a schema change to these columns would invalidate the connecting-signal test and the union-of-hard-clusters rule.
- `sql_table:customer_accounts` — Actor identity (actor axis) and home_latitude/home_longitude context for separating remote-shopping (soft) from observed-location fraud; the connecting-signal test compares actors across clusters.
- `sql_table:stores` — Store branch-location axis cited by the 'do not compute travel from store/target coordinates' rule that sits alongside the edited cardinality bullets.
- `sql_table:shopping_baskets` — Basket/customer/store joins and archive context; a repeated basket is one of the cross-actor connecting signals that classifies two clusters as one incident in rule 15.
- `sql_table:shopping_basket_items` — Basket resource lines (requested_quantity) for the quantity/resource reconciliation invariant, a hard family whose clusters the union rule covers.
- `sql_table:payment_transaction_items` — Line-level reconciliation (purchased_quantity, item_unit_price_cents) for the amount-vs-lines hard family whose clusters the union rule covers.
- `sql_table:product_variants` — Catalogue price joins for the amount/line invariant checks referenced by the hard sweep.
- `sql_table:store_inventory` — Reserve/availability arithmetic and store/SKU resource axis for the General Risk Primitives section.
- `sql_table:return_requests` — Return/payment/basket/customer workflow joins for the broader risk invariants in the General Risk Primitives section.
- `workspace:/proc/payments/README.md` — Defines that observed_lat/observed_lon are checkout-time risk-log coordinates (not address) and that fingerprints are opaque - the load-bearing semantics behind the travel/burst hard families and the identifier-collision connecting-signal test in rule 15.
- `workspace:/proc/customers/README.md` — Coarse customer home-area coordinate semantics used to keep observed-vs-home distance a soft signal in the location rules that feed the hard/soft gate.
- `workspace:/proc/stores/README.md` — Store branch-coordinate semantics for the payment-risk distance checks referenced by the location rules.
