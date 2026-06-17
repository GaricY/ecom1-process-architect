# Fraud Risk Review

## When this process applies

Read this process for fraud, risk, anomaly, Risk-Ops, archived-payment review, "identify the fraudulent records", "mark every suspicious payment", or any plural task that asks for a complete risk cohort. It is an information/discovery BP. It does not authorize payment mutation and does not own final refs or submission.

After finding the cohort, use [refs](refs.md) to build citations and [submission_terminal](submission_terminal.md) to submit.

## Inputs

- `bin-help/sqlite_schema.txt` - full schema and SQL conventions.
- SQL tables: especially `payments`, `stores`, `baskets`, `payment_lines`, and `products`.
- `/docs/payments/3ds.md` - legitimate 3DS state transitions for payment workflow-state invariants.

## Process

1. Define the task scope first: archived payments only, one store, one day, one customer, one campaign, or whatever the brief names. Record the scope predicate and universe size in scratchpad.
2. Read the full column list for the in-scope table from `bin-help/sqlite_schema.txt`. Do not search only columns whose names sound like "fraud".
3. Enumerate signal families before choosing an answer:
   - record-internal invariants: amount vs lines, archive flags, terminal status with inconsistent workflow columns;
   - workflow-state invariants: `paid` rows carrying failed/pending 3DS columns, exhausted attempts, impossible state transitions under the topic doc;
   - cross-record duplicates: shared `payment_method_fingerprint`, shared `device_fingerprint`, repeated baskets, identical timestamps across actors;
   - cross-table joins: payment amount vs product prices, payment store vs joined store, basket/customer mismatch;
   - time/sequence invariants: impossible travel, bursts, store-hours or dense short-window patterns.
4. Run every plausible signal and record zero-result signals too. Empty PMF/DFP/amount results are evidence that the cohort may live in a workflow-state column, not permission to submit the first fuzzy hit.
5. Prefer discrete or structural signals over smooth thresholds:
   - exact shared value: one PMF/DFP, one status value, one basket id;
   - structural condition: every record paired by an impossible-travel query, duplicate-payment query, or invariant-violation query;
   - threshold-only band: distance/amount/count cutoffs with no shared identifier. Use only as support unless it has a sharp break or refines to a dense actor/window cluster.
6. For location signals, sweep both axes when the schema exposes them:
   - actor/device axis such as `observed_lat` / `observed_lon`;
   - claimed-entity axis such as joined `stores.lat` / `stores.lon`.
   Union the matches. A stationary burst can keep observed coordinates fixed while rotating `store_id`; an observed-only sweep misses that MO.
7. For high-count threshold signals, regroup by `(actor_id, short_time_window)` before discarding as noise. A 100+ row fuzzy band can hide a dense 10+ record burst for one actor inside a broad legitimate tail.
8. Include every member of inseparable evidence groups. If a signal flags a pair or duplicate group and the data does not identify the sole offender, both members belong in the candidate cohort.
9. Union disjoint sub-clusters that share the same structural signal inside the task scope. Do not keep only the strongest sub-cluster because it has the largest distance, count, or amount.
10. Interpret "one hit" / "one incident" as one connected campaign window, not one record. Default to one connected 1-3 week window; drop isolated sub-clusters 4+ weeks away unless the brief explicitly widens the scope.
11. Run the final cohort query without `LIMIT` or with a bound far above the plausible cohort size and confirm it did not truncate.

## Coverage check before refs/submission

Scratchpad must show:

- scope predicate and universe size;
- full column list considered;
- signal families run, including zero-result families;
- match counts per signal and per coordinate axis where applicable;
- whether each match set has an exact identifier, structural condition, or threshold-only band;
- disjoint sub-cluster count and temporal span;
- final cohort count with no truncation.

The message records and `refs` records must be the same set.

## Outcomes

- `OUTCOME_OK`: complete cohort or requested risk answer found and cited.
- `OUTCOME_NONE_CLARIFICATION`: the brief does not define enough scope to choose between multiple plausible cohorts.
- `OUTCOME_NONE_UNSUPPORTED`: the requested risk action requires a mutation or policy not present in the runtime.
- `OUTCOME_DENIED_SECURITY`: only when the task asks to expose private customer/contact data outside the allowed boundary.

## Refs to set in scratchpad

- Every `/proc/...` record marked in the answer.
- The topic policy doc if a workflow-state invariant from that policy was applied, commonly `/docs/payments/3ds.md`.
- Public store/catalogue records only when the request or evidence explanation relies on them.
- Then run [refs](refs.md) for final citation safety.

## Anti-patterns

- Stopping at the first non-empty anomaly query.
- Searching only PMF/DFP/distance columns and skipping workflow-state columns.
- Submitting a threshold-only distance band with no discrete or structural confirmation.
- Sweeping only observed coordinates when a store coordinate axis exists.
- Dropping smaller sub-clusters of the same structural signal.
- Using `LIMIT 10` or `LIMIT 20` on the query that drives the final answer.
- Treating "one hit" as one record or one actor.

## Dependencies

> If any of these dependencies change, this BP file may have become stale and must be re-derived.

- `/docs/payments/3ds.md` - legitimate 3DS workflow-state transitions used for payment invariant checks.
- `/bin/sql` (`--help`) - SQL interface and schema-discovery contract.
- SQL table `payments` - primary risk record and payment anomaly columns.
- SQL table `stores` - joined store location axis for geo anomaly checks.
- SQL table `baskets` - basket/customer/store joins and archive context.
- SQL table `payment_lines` - line-level reconciliation for amount anomalies.
- SQL table `products` - catalogue price joins for amount/line checks.
