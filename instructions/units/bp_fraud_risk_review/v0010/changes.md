# bp_fraud_risk_review v0010

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-22T10:17:38+00:00`
- parent: `v0009`

## Rationale

Owning layer: domain_policy (this topic BP defines the fraud hard-signal families and cohort membership). Decomposing the trial: observed_lat/observed_lon track each row's store branch (e.g. innsbruck-ost=47.27,11.43; vie-favoriten=48.15,16.38), so the true cohort is the two cross-actor device rings (12 rows) plus one customer's full 5-store burst (5 rows) = EUR 5458.30; the Executor recovered 12 device + 3 of 5 burst rows = EUR 4678.50 = 85.7% ('~86%'), and emitted 12 store-to-store 'impossible travel' pairs as the 'up to ten false positives'. The conflicting v0009 (also from v0008) already (a) reclassifies a timestamp-only cross-actor match as soft and (b) expands an impossible-travel hit to the whole contiguous rapid run — fix (b) recovers this trial's two dropped slow-hop burst rows, so I keep both v0009 changes verbatim. But v0009 still computes travel from a moving observed axis and gates the burst on 'small observed spread', so on a store-pinned axis it would (1) keep all 12 false-positive store-to-store pairs as hard travel and (2) reject the genuine store-pinned burst (its spread is large). Extending v0009: impossible travel is hard only on an independent observed axis; a store-pinned axis carries no travel signal and routes store-to-store jumps to the burst test; the burst test is the distinct-target count in a dense window, not observed spread; a lone two-event store-to-store jump is soft-only. I also correct the stale `catalog` table reference to `prod` (the reconciliation table present in this trial's schema). This is a focused extension of v0009 in the same layer, not a stacked compensating safeguard.

## Rollback

Create a new version from bp_fraud_risk_review v0009 content if scoping impossible-travel to an independent observed axis or redefining the burst test by distinct-target count misclassifies cohorts in another trial (v0009 keeps travel computed from any moving observed axis and gates the burst on small observed spread).

## Dependencies
- `workspace:/docs/payments/3ds.md` — Backs the retained workflow-state invariant family (status==paid carrying failed/pending three_ds, exhausted attempts, impossible 3DS transitions); if legitimate 3DS transitions change, that hard-signal family goes stale.
- `sql_table:payment-ledger` — Primary risk record; every edited geo/collision rule reads customer_id/store_id/created_at/observed_lat/observed_lon plus device/payment fingerprints and amount_cents from this family.
- `sql_table:locations` — Branch lat/lon is the reference for the added store-pinned-observed test (observed point == store branch coordinate) and for store-distance/reserve arithmetic in the record-invariant family.
- `sql_table:carts` — Record-invariant family uses payment-cart joins and archive context; a schema change here can stale that rule.
- `sql_table:return-workflows` — Record-invariant family uses payment-return joins; a schema change here can stale that rule.
- `sql_table:prod` — price_cents catalogue join for the amount/line reconciliation invariant; this is the warehouse table present in the current schema (replaces the stale `catalog` name).
