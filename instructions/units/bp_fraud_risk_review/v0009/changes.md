# bp_fraud_risk_review v0009

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-22T07:03:13+00:00`
- parent: `v0008`

## Rationale

Owning layer: domain_policy (this topic BP defines the fraud hard-signal families and cohort membership). The trial failed on two fronts at once: ~9% of the fraud EUR was missed and several cited rows were false positives. (1) Over-capture: the cross-actor exact-identifier collision family listed 'identical created_at across different customer_id' as a HARD signal, so the Executor cited two payments (different device/payment fingerprint, store and amount) that merely shared a second-resolution timestamp — a coincidence, not an identity. This rule was carried verbatim since v0005 (never a deliberate fix), so narrowing it is not re-litigating a prior change. I drop the timestamp clause from the hard family and reclassify a timestamp-only cross-actor match as soft-only. (2) Under-capture: impossible-travel membership was pairwise (only the rows bracketing each over-threshold hop), so a trailing event of one actor's rapid multi-city run that landed near its immediate neighbour was dropped despite being the same dense run. I extend the impossible-travel scan-shape rule to expand a hit to the whole contiguous rapid run for that actor (mirroring the stationary-burst expansion already in step 9). Two surgical edits to existing rules plus matching anti-patterns and one coverage-check line; no new families added.

## Rollback

Create a new version from v0008 content if the narrowed timestamp rule or the impossible-travel run-expansion proves wrong (v0008 keeps identical-created_at as a hard collision and pairwise travel membership).

## Dependencies
- `sql_table:payment-ledger` — Every rule changed by this fix reads payment-ledger fields: payment_method_fingerprint/device_fingerprint and basket_id/order_id for the cross-actor collision family, and customer_id/created_at/observed_lat/observed_lon for the impossible-travel run expansion. A change to this record shape would make the corrected rules wrong.
- `workspace:/docs/payments/3ds.md` — Backs the retained workflow-state invariant family in this BP (status==paid carrying failed/pending three_ds, exhausted attempts, impossible 3DS transitions); if the legitimate 3DS transitions change, that hard-signal family goes stale.
