# bp_fraud_risk_review v0011

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-22T12:31:59+00:00`
- parent: `v0010`

## Rationale

Owning layer: domain_policy (this topic BP defines the fraud hard-signal families and cohort membership). This is a PA regression in the same task family, not a fresh fix. v0010 was itself a process_architect failure-fix for an archive-fraud trial whose symptom was 'recovered ~86% of fraud EUR and marked up to ten false positives'; it cured the under-capture by making the single-actor burst hard on distinct-target count alone and explicitly removing any disqualifier on a store-pinned axis. The current trial fails worse with the mirror symptom ('~100% of fraud EUR recovered, more than ten false positives'): two in-scope actors each rotate many distinct stores inside a five-minute window on a store-pinned observed axis, so the bare distinct-store burst test fired on BOTH and the Executor cited the entire export. Per the regression rule I narrow v0010's over-broad burst test rather than stack another safeguard. The true discriminator the Executor never computed is an exact-identifier anomaly: the genuine fraud actor's dense run is one device_fingerprint cycling many distinct payment_method_fingerprints (card-testing enumeration), while the false-positive actor keeps one consistent device_fingerprint+payment_method_fingerprint per identity and only rotates stores. The Executor checked solely cross-actor fingerprint collisions (zero) and so missed the enumeration backbone. Two coordinated edits in this one layer: (1) make single-actor payment-instrument/device enumeration an explicit hard hit in the exact-identifier family; (2) require an exact-identifier backbone (enumeration or cross-actor reuse) before a store-pinned multi-store burst is hard, classifying a stable-identity store-rotation run as soft store-rotation/decoy context. I do NOT re-add v0008's observed-spread disqualifier (correctly removed in v0010 because store-pinned bursts have large spread) — I widen the rule on a different axis (identifier backbone). Cross-actor device rings and independent-axis impossible travel remain hard, so prior-trial cohorts that carried an identifier anomaly are unaffected. I also realign the family-name references and dependency set from v0010's stale `locations`/`return-workflows`/`prod` to this world's schema names `stores`/`returns`/`catalog`.

## Rollback

Create a new version from bp_fraud_risk_review v0010 content if requiring an exact-identifier backbone for a store-pinned burst misclassifies a genuine stable-identity burst as soft in another trial (v0010 treats distinct-target count alone as a hard burst regardless of identifier structure).

## Dependencies
- `workspace:/docs/payments/3ds.md` — Backs the retained workflow-state invariant family (status==paid carrying failed/pending three_ds, exhausted attempts, impossible 3DS transitions); if legitimate 3DS transitions change, that hard-signal family goes stale.
- `sql_table:payment-ledger` — Primary risk record; both edited rules read customer_id/store_id/created_at/observed_lat/observed_lon plus device_fingerprint and payment_method_fingerprint and amount_cents from this family, including the new per-actor distinct-payment-fingerprint enumeration count.
- `sql_table:stores` — Branch lat/lon is the reference for the store-pinned-observed test (observed point == store branch coordinate) that the narrowed burst rule depends on, plus inventory on_hand/reserved for the record-invariant family.
- `sql_table:carts` — Record-invariant family uses payment-cart joins and archive context; a schema change here can stale that rule.
- `sql_table:returns` — Record-invariant family uses payment-return joins; a schema change here can stale that rule.
- `sql_table:catalog` — price_cents catalogue join for the amount/line reconciliation invariant; this is the warehouse table present in the current schema.
