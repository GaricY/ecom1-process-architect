# bp_fraud_risk_review v0009

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-18T18:46:22+00:00`
- parent: `v0008`

## Rationale

Owning layer: domain_policy/topic_evidence in the fraud topic BP (the hard-sweep collision family). The grader flagged TWO defects in this trial: the cohort recovered only ~95% of true fraud EUR (under-capture) AND marked more than ten payments as false positives (over-capture). The conflicting v0008 already fixes the under-capture by redefining impossible travel as a speed criterion and expanding a fired hop to the whole consecutive impossible-speed chain. But v0008 leaves the cross-actor identifier-collision family untouched: its step 4 still lists a shared device_fingerprint as a hard collision, and that is exactly what produced the >10 false positives here. With ZERO cross-actor payment_method_fingerprint collisions, the Executor promoted two device_fingerprint groups (each shared by 6 distinct customers, 12 rows, ~EUR 9964) to the hard cohort. A payment instrument cannot belong to multiple unrelated actors, but a device routinely is shared (in-store terminals/kiosks/service desks report one device for everyone who pays there; household/public/app devices are shared), and a pooled device's observed coordinates cannot be read as one device travelling. This is an EXTEND of v0008, not a replace: I keep its travel-chain rule verbatim and add the missing instrument-vs-device distinction to step 4, the step 7 hard/soft taxonomy, the per-record map (step 16), the General Risk Primitives, the coverage check, the considered_not_cited ledger role, and two anti-patterns. The distinction is new to this unit (v0005 schema-rename, v0006 proc-semantics, v0007 refs-refactor never introduced or reverted it), so nothing is being re-litigated.

## Rollback

Create a new version from v0008 content if demoting cross-actor device_fingerprint collisions to soft causes real device-ring fraud to be missed in a later trial; this restores v0008's travel fix without the instrument-vs-device distinction.

## Dependencies
- `workspace:/docs/payments/3ds.md` — Defines the legitimate 3DS workflow-state transitions used by the payment workflow-state-invariant hard family.
- `sql_table:payment_transactions` — Primary risk record; supplies payment_method_fingerprint and device_fingerprint whose hard-vs-soft distinction this edit rewrites, plus observed coordinates and the archive flag the travel rule computes speed from.
- `sql_table:customer_accounts` — Actor identity and home-coordinate context used to separate remote shopping from observed-location fraud in the soft/hard discriminator.
- `sql_table:stores` — Joined store location axis for geo anomaly checks; referenced to keep observed-to-observed travel separate from store distance.
- `sql_table:shopping_baskets` — Basket/customer/store joins and archive context for the record/table invariant family.
- `sql_table:shopping_basket_items` — Basket resource lines (requested_quantity) for quantity/resource reconciliation invariants.
- `sql_table:payment_transaction_items` — Line-level reconciliation (purchased_quantity, item_unit_price_cents) for amount-anomaly invariants, including archived payment line snapshots.
- `sql_table:product_variants` — Catalogue price joins for amount/line invariant checks.
- `sql_table:store_inventory` — Reserve/availability arithmetic and store/SKU resource axis for the general risk primitives.
- `sql_table:return_requests` — Return/payment/basket/customer workflow joins for the general risk primitives.
- `workspace:/proc/payments/README.md` — States that payment fingerprints are opaque instrument/device identifiers and that observed coordinates are checkout-time risk-log values; load-bearing for both the instrument-vs-device collision distinction and the observed-speed travel rule.
- `workspace:/proc/customers/README.md` — Coarse home-area coordinate semantics used to keep observed-vs-home distance signals soft.
- `workspace:/proc/stores/README.md` — Store branch coordinate semantics for payment-risk/distance checks, referenced when distinguishing store distance from observed travel.
