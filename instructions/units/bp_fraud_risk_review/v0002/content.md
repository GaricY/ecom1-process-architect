# Fraud Risk Review

## When this process applies

Read this process for fraud, risk, anomaly, Risk-Ops, archived-payment review, "identify the fraudulent records", "mark every suspicious payment", or any plural task that asks for a complete risk cohort. It is an information/discovery BP. It does not authorize payment mutation and does not own final refs or submission.

After finding the cohort, use [refs](refs.md) to build citations and [submission_terminal](submission_terminal.md) to submit.

## Inputs

- `bin-help/sqlite_schema.txt` - full schema and SQL conventions.
- SQL tables: especially `payments`, `customers`, `stores`, `baskets`, `payment_lines`, and `products`.
- `/docs/payments/3ds.md` - legitimate 3DS state transitions for payment workflow-state invariants.

## Process

1. Define the task scope first: archived payments only, one store, one day, one customer, one campaign, or whatever the brief names. Record the scope predicate and universe size in scratchpad.
2. Read the full column list for the in-scope table from `bin-help/sqlite_schema.txt`. Do not search only columns whose names sound like "fraud".
3. Enumerate signal families before choosing an answer:
   - record-internal invariants: amount vs lines, archive flags, terminal status with inconsistent workflow columns;
   - workflow-state invariants: `paid` rows carrying failed/pending 3DS columns, exhausted attempts, impossible state transitions under the topic doc;
   - cross-record duplicates: shared `payment_method_fingerprint`, shared `device_fingerprint`, repeated baskets, identical timestamps across actors;
   - cross-table joins: payment amount vs product prices, payment store vs joined store, basket/customer mismatch;
   - time/sequence invariants: impossible travel, bursts, store-hours or dense short-window patterns;
   - location-axis checks: observed-to-observed movement, observed-to-store distance, and observed-to-customer-home context when `customers` exposes home coordinates.
4. Run every plausible hard-signal family and record zero-result signals too. A zero-result exact collision or invariant query is evidence against using that signal in the final explanation.
5. Classify candidate match sets before building the final cohort:
   - hard-supported: exact identifier collision across actors, impossible observed travel, dense stationary multi-store burst, workflow-state invariant, or record/table invariant;
   - soft-only: one new device or payment fingerprint for one actor, high amount, high purchase count, distant observed-vs-store band, long busy timeline, or any smooth threshold band with no structural confirmation.
6. Only hard-supported records may enter the final cohort. Soft-only records are excluded by default, even when they look suspicious, are high value, or sit near a true incident window.
7. For location signals, keep the axes separate:
   - observed-to-observed movement between sequential payments by the same actor can be hard evidence when the movement is physically impossible for the elapsed time;
   - observed-to-store distance is support only, because stable observed coordinates near the customer home while stores are distant can be ordinary remote shopping;
   - a stationary observed point with many different stores or cities inside a few minutes can be hard evidence of a coordinated burst.
8. For high-count fuzzy signals, regroup by `(actor_id, short_time_window)` before discarding as noise. A broad legitimate tail can hide a dense hard-supported burst, but the broad tail itself must not be cited unless it passes the hard gate.
9. Include every member of inseparable hard evidence groups. If a hard signal flags a pair or duplicate group and the data does not identify the sole offender, both members belong in the candidate cohort.
10. Union disjoint sub-clusters only when each sub-cluster has its own hard signature or shares a verified hard signature with the incident. Do not keep only the strongest hard sub-cluster because it has the largest distance, count, or amount.
11. Interpret "one hit" / "one incident" as one evidence-connected campaign, not one pure date window. Time span is a sanity check after hard membership is established; it is not a reason to add soft-only clusters.
12. Build a per-record evidence map before refs. Each cited record must have a path, hard signal name, query/condition, and cluster id. Remove any record whose only justification is narrative, threshold-only, customer-level suspicion, or temporal proximity.
13. Run the final cohort query without `LIMIT` or with a bound far above the plausible cohort size and confirm it did not truncate.

## Coverage check before refs/submission

Scratchpad must show:

- scope predicate and universe size;
- full column list considered;
- signal families run, including zero-result families;
- match counts per signal and per coordinate axis where applicable;
- hard-supported vs soft-only classification for each match set;
- per-record evidence map for the final cohort;
- disjoint hard sub-cluster count and temporal span;
- confirmation that no final record is supported only by a soft signal;
- final cohort count with no truncation.

The message records and `refs` records must be the same pruned set.

## Outcomes

- `OUTCOME_OK`: complete hard-supported cohort or requested risk answer found and cited.
- `OUTCOME_NONE_CLARIFICATION`: the brief does not define enough scope to choose between multiple plausible hard-supported cohorts.
- `OUTCOME_NONE_UNSUPPORTED`: the requested risk action requires a mutation or policy not present in the runtime.
- `OUTCOME_DENIED_SECURITY`: only when the task asks to expose private customer/contact data outside the allowed boundary.

## Refs to set in scratchpad

- Every `/proc/...` record marked in the answer.
- The topic policy doc if a workflow-state invariant from that policy was applied, commonly `/docs/payments/3ds.md`.
- Public customer/store/catalogue records only when the request or evidence explanation relies on them.
- Then run [refs](refs.md) for final citation safety.

## Anti-patterns

- Stopping at the first non-empty anomaly query.
- Searching only PMF/DFP/distance columns and skipping workflow-state columns.
- Submitting a threshold-only distance band with no discrete or structural confirmation.
- Treating a new device, high amount, or one actor's long busy timeline as fraud without a hard signal.
- Treating stable observed-home plus distant store as fraud without impossible movement or dense multi-store burst evidence.
- Sweeping only observed coordinates when a store coordinate axis exists.
- Unioning a soft-only cluster into a true incident because it is nearby in time, amount, customer family, or narrative similarity.
- Dropping smaller hard-supported sub-clusters of the same incident.
- Using `LIMIT 10` or `LIMIT 20` on the query that drives the final answer.
- Treating "one hit" as one record, one actor, or one date window.
- Inventing shared PMF/DFP, workflow, or geo evidence that was not returned by a query.

## Dependencies

> If any of these dependencies change, this BP file may have become stale and must be re-derived.

- `/docs/payments/3ds.md` - legitimate 3DS workflow-state transitions used for payment invariant checks.
- `/bin/sql` (`--help`) - SQL interface and schema-discovery contract.
- SQL table `payments` - primary risk record, fingerprints, timestamps, status, observed coordinates, and 3DS columns.
- SQL table `customers` - customer identity and home-coordinate context for distinguishing remote shopping from observed-location fraud.
- SQL table `stores` - joined store location axis for geo anomaly checks.
- SQL table `baskets` - basket/customer/store joins and archive context.
- SQL table `payment_lines` - line-level reconciliation for amount anomalies.
- SQL table `products` - catalogue price joins for amount/line checks.
