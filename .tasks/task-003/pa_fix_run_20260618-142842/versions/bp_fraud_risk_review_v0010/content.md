# Fraud Risk Review

## When this process applies

Read this process for fraud, risk, anomaly, Risk-Ops, archived-payment review, "identify the fraudulent records", "mark every suspicious payment", or any plural task that asks for a complete risk cohort. It is an information/discovery BP. It does not authorize payment mutation and does not own final refs projection or submission.

After finding the cohort, classify the Evidence ledger and use [refs](refs.md) to project citations and [submission_terminal](submission_terminal.md) to submit.

## Inputs

- `bin-help/sqlite_schema.txt` - full schema and SQL conventions.
- SQL tables: especially `payment_transactions`, `customer_accounts`, `stores`, `shopping_baskets`, `shopping_basket_items`, `payment_transaction_items`, `product_variants`, `store_inventory`, and `return_requests`.
- `/docs/payments/3ds.md` - legitimate 3DS state transitions for payment workflow-state invariants.
- `/proc/payments/README.md`, `/proc/customers/README.md`, `/proc/stores/README.md` - source semantics for archived payments, payment observed coordinates/fingerprints, customer home-area coordinates, and store branch coordinates.

**Schema note.** The schema was renamed; the payment risk columns this BP leans on are now `payment_transactions.payment_created_at` (event time), `observed_latitude` / `observed_longitude` (checkout-time risk-log coordinates, not customer address), `is_archived_basket_reference` (archive flag), `payment_status` (workflow state), `record_path` (cite path), and the unchanged opaque exact identifiers `payment_method_fingerprint` / `device_fingerprint` plus `three_ds_status` / `three_ds_attempts` / `three_ds_max_attempts`. Customer `home_latitude` / `home_longitude` are coarse home-area coordinates used by risk fixtures; store coordinates are branch coordinates for distance checks. Read the current column list from `bin-help/sqlite_schema.txt` before composing a query.

## Process

1. Define the task scope first: archived payments only, one store, one day, one customer, one campaign, or whatever the brief names. Record the scope predicate and universe size in scratchpad.
2. The analysis scope is the user's predicate, not a suspect found mid-analysis. If the brief says archived payments, every mandatory hard family scans all archived payments. A customer, date, store, device, or identifier surfaced by one family is a candidate cluster only; it must not narrow the remaining hard-family scans.
3. Read the full column list for the in-scope table from `bin-help/sqlite_schema.txt`. Do not search only columns whose names sound like "fraud". Identify the actor, event time, observed location, claimed target, exact identifier, resource, and workflow-state columns that exist.
4. Before choosing an answer, run the mandatory hard sweep and record each family as `zero`, `hard hit`, or `not applicable` because required columns are absent:
   - cross-actor exact identifier collisions: shared `payment_method_fingerprint`, shared `device_fingerprint`, repeated baskets, identical timestamps, or other exact values across actors;
   - workflow-state invariants: `paid` rows carrying failed/pending 3DS columns, exhausted attempts, or impossible state transitions under the topic doc;
   - record/table invariants: amount vs lines/products, archive flags, payment vs basket/customer/store joins, inventory/reserve arithmetic, return/payment/basket joins, duplicate payments. Missing live basket files on archived payments are not hard mismatches by themselves; use the payment line snapshot / `payment_transaction_items`;
   - impossible observed travel: sequential events by the same actor whose observed coordinates move impossibly far for the elapsed time;
   - stationary single-actor multi-target burst: one actor with many events at many distinct claimed targets, stores, cities, or resources inside minutes while observed coordinates remain nearly stationary.
5. For every hard-sweep family, the ledger must record the query shape, not only the result: scan scope, actor axis, time axis, coordinate/target axis, window definition, and max-metric used to validate zero results.
6. Finding one hard-supported cluster is not enough to submit. Continue the mandatory hard sweep until every family above has a recorded result and trustworthy query shape.
7. Classify candidate match sets before building the final cohort:
   - hard-supported: exact identifier collision across actors, impossible observed travel, stationary single-actor multi-target burst, workflow-state invariant, or record/table invariant;
   - soft-only: one new device or payment fingerprint for one actor, high amount, high purchase count, distant observed-vs-store or observed-vs-home band, long busy timeline, or any smooth threshold band with no structural confirmation.
8. Only hard-supported records may enter the final cohort. Soft-only records are excluded by default, even when they look suspicious, are high value, or sit near a true incident window.
9. For location/target signals, keep the query shapes separate:
   - impossible observed travel is an observed-to-observed check across all actors in scope: partition by actor/customer, order by event time, compare consecutive observed coordinates, and compute elapsed time. The consecutive-pair comparison is only a detector. When it flags an actor, the fraud unit is that actor's dense anomaly window — the tight time span in which that actor's observed coordinates cannot be reconciled to one trajectory (one identity present at impossibly-separated places). Expand the hit to every archived row of that actor inside that window, including rows whose neighbouring transition is same-location or fell just outside the pairwise time gate; never cite only the two rows that bracket a flagged jump while dropping the rest of the window;
   - a confirmed travel incident is a dense moving burst: one actor rotating through several distinct, impossibly-separated observed locations within minutes (large observed spread, unlike the stationary burst below). A single isolated two-event crossing — the actor's only events in the window, with no surrounding dense rotation and no other hard-family signal on the same actor or rows — is not by itself a confirmed incident, however large the distance; record it as a soft candidate in `considered_not_cited` and corroborate before citing. This does not weaken inseparable-group inclusion once a cluster is genuinely confirmed;
   - do not compute impossible travel from store, customer home-area, or other claimed target coordinates. Fast rotation through distant stores with stable observed coordinates is a burst/tempo anomaly, not observed travel;
   - stationary single-actor burst is grouped by one actor/customer, not by one store and not by multiple customers. The window is a dense sub-window from each event, not `MAX(payment_created_at) - MIN(payment_created_at)` over the actor's whole history. Count events, distinct stores/targets/resources, and distinct cities when joined; confirm observed-coordinate spread inside the window is small; expand a hard hit to all in-window records for that actor without `LIMIT`.
10. Stable observed coordinates are not automatically soft. Stable observed plus distant stores or distant customer home-area at ordinary cadence is remote shopping context; stable observed plus many distinct stores, cities, targets, or resources within minutes is a hard tempo anomaly. The discriminator is short-window target rotation, not observed-to-store/home distance alone.
11. When a mandatory hard family returns zero, validate the negative. Record the top max-metric for that family, not only `zero`: for travel, the largest same-actor observed speed or observed jump in scope; for burst, the largest same-actor short-window distinct-target count and observed spread. If the max-metric contradicts the zero result, fix the query before trusting the ledger.
12. For high-count fuzzy signals, regroup by `(actor_id, short_time_window)` before discarding as noise. A broad legitimate tail can hide a dense hard-supported burst, but the broad tail itself must not be cited unless it passes the hard gate.
13. Include every member of inseparable hard evidence groups. If a hard signal flags a pair or duplicate group and the data does not identify the sole offender, both members belong in the candidate cohort. This applies once a cluster is confirmed hard; it does not promote a lone isolated two-event travel crossing (rule 9) into a confirmed incident on its own.
14. After the hard gate, the final cohort is the union of every hard-supported cluster in scope - both every sub-cluster of a single evidence-connected incident AND every separate incident that independently clears the hard gate. Different hard families may surface different sub-clusters of one incident or different incidents entirely; include all of them and never submit only the first, largest, cleanest, tightest-window, or highest-count one. A connecting signal (rule 15) tells you whether two clusters are the *same* incident or two independent incidents - it labels the evidence map; it does not gate citation. Both connected sub-clusters and unconnected independent hard incidents belong in refs.
15. "One hit" / "one incident" / "one record" in a discovery brief is an existence assurance - fraud IS present, go find the fraudulent records - not a cap that lets you cite one cluster and discard another that independently clears the hard gate. Membership is decided by the hard gate (rules 7-13), not by the singular phrasing. A connecting signal (shared actor, shared exact identifier - `payment_method_fingerprint`, `device_fingerprint`, a repeated basket - or another confirmed cross-actor collision) only classifies two clusters as one incident vs. two independent incidents; either way each cluster that clears the hard gate is cited. Do NOT drop a fully hard-supported cluster (confirmed dense travel burst, stationary multi-target burst, identifier collision, or record/state invariant) because it is unconnected to a larger cluster, falls on a different date, uses a different MO, or has fewer records or a looser window than a competitor - a tighter or larger stationary burst never displaces a separately-confirmed travel burst, and vice versa. What a singular brief DOES exclude is soft material (lone two-event crossings, threshold-only bands, high amount or busy-timeline alone); the hard gate already removes those, so route them to `considered_not_cited`. Fall back to `OUTCOME_NONE_CLARIFICATION` only when two candidate cohorts are mutually-exclusive readings of the *same* records (citing both would be self-contradictory) and the brief gives no basis to choose - not merely because two independent hard incidents both exist. When the brief states no cardinality, this same union stands.
16. Build a per-record evidence map before refs. Each cited record must have a path, hard signal name, query/condition, and cluster id. Remove any record whose only justification is narrative, threshold-only, customer-level suspicion, or temporal proximity.
17. Run the final cohort query without `LIMIT` or with a bound far above the plausible cohort size and confirm it did not truncate.

## Risk Investigation Tricks

Use these as query-shape references, not as fixed thresholds or a payment-only cookbook. Adapt table and column names to the current schema, and keep the user's scope predicate intact.

### Observed Travel Shape

Use this shape for physical movement. It compares observed event coordinates for the same actor over time. It does not use store or other claimed target coordinates.

```sql
with seq as (
  select p.*,
         lag(record_path) over(partition by customer_id order by payment_created_at, payment_id) as prev_path,
         lag(payment_created_at) over(partition by customer_id order by payment_created_at, payment_id) as prev_ts,
         lag(observed_latitude) over(partition by customer_id order by payment_created_at, payment_id) as prev_lat,
         lag(observed_longitude) over(partition by customer_id order by payment_created_at, payment_id) as prev_lon
  from payment_transactions p
  where is_archived_basket_reference = 1
),
jumps as (
  select customer_id, prev_path, record_path, prev_ts, payment_created_at,
         (julianday(payment_created_at) - julianday(prev_ts)) * 24 * 60 as minutes,
         abs(observed_latitude - prev_lat) + abs(observed_longitude - prev_lon) as observed_l1
  from seq
  where prev_path is not null
)
select *
from jumps
where minutes between 0 and 15
  and observed_l1 > 2.0
order by customer_id, payment_created_at;
```

If this shape returns zero, record the largest same-actor observed jump/speed in the same scope before trusting the zero.

This query surfaces only *adjacent* impossible transitions; it is a detector, not the cohort. Once it flags an actor, re-extract that actor's full dense anomaly window — every archived row within the tight span around the flagged transition where the actor's observed locations cannot be reconciled to one trajectory — and cite the whole window-cluster. Non-adjacent rows, same-city rows inside the window, and rows whose neighbour transition fell just outside the pairwise gate all belong to the incident; citing only the bracketing pair undercounts both the cohort and the answer amount. Conversely, confirm the window is a genuine multi-event rotation across distinct locations: a lone two-event crossing for an actor with no surrounding cluster and no other hard-family hit is a soft candidate, not a confirmed incident — keep it in `considered_not_cited` unless corroborated. A confirmed dense travel burst stays in the cohort even when a stationary burst by a *different* actor also exists; the two are independent hard incidents, not competitors (rule 15).

### Stationary Single-Actor Burst Shape

Use a rolling/self-join sub-window. Do not aggregate over the actor's whole history and call `MAX(payment_created_at) - MIN(payment_created_at)` the burst window.

```sql
with pairs as (
  select a.customer_id,
         a.payment_created_at as start_ts,
         b.record_path,
         b.payment_created_at,
         b.store_id,
         abs(a.observed_latitude - b.observed_latitude) + abs(a.observed_longitude - b.observed_longitude) as observed_l1
  from payment_transactions a
  join payment_transactions b
    on a.customer_id = b.customer_id
   and b.payment_created_at >= a.payment_created_at
   and (julianday(b.payment_created_at) - julianday(a.payment_created_at)) * 24 * 60 between 0 and 5
  where a.is_archived_basket_reference = 1
    and b.is_archived_basket_reference = 1
),
windows as (
  select customer_id, start_ts,
         count(*) as payment_count,
         count(distinct store_id) as distinct_stores,
         max(observed_l1) as observed_spread_l1
  from pairs
  group by customer_id, start_ts
)
select *
from windows
where distinct_stores >= 4
  and observed_spread_l1 < 0.05
order by distinct_stores desc, payment_count desc, start_ts;
```

If this shape returns a hard hit, expand the final cluster to all in-window records for that actor. If it returns zero, record the top short-window `distinct_stores`, `payment_count`, and `observed_spread_l1` from the same sliding-window shape.

The stationary shape requires a *small* `observed_spread_l1`; it deliberately excludes the moving multi-location burst (one actor at several impossibly-separated places in a tight window). Do not conclude "no burst" from a zero here — a large short-window `distinct_stores`/`distinct_cities` with a *large* observed spread is a moving travel burst and belongs to the impossible-travel family above, where its full window-cluster is the cohort.

### General Risk Primitives

For new risk angles such as delivery, reservation, refund, inventory, or non-3DS payment flows, first map the schema into these axes:

- actor axis: customer, device, payment method, staff/runtime actor, delivery actor, or reservation owner;
- claimed target axis: store, delivery stop, pickup point, inventory store, basket store, or other named destination/resource owner;
- event time axis: payment time, basket time, return time, delivery time, reservation time, or workflow transition time;
- resource axis: SKU, basket, payment, return, inventory row, delivery item, or reserved stock;
- invariant axis: amount/lines, basket/customer/store joins, inventory/reserve arithmetic, return/payment/basket joins, and workflow state under the relevant `/docs/...` policy.

Then apply the same hard primitives: impossible observed movement for one actor, too many claimed targets/resources in a short sub-window for one actor, exact identifier collision across actors, ledger reconciliation across tables, and policy/workflow-state invariant. Tables such as `store_inventory`, `shopping_basket_items`, and `return_requests` are current examples for resource/invariant checks; future delivery tables should be added to dependencies only when the BP explicitly references them.

## Coverage check before ledger/submission

Scratchpad must show:

- scope predicate and universe size;
- full column list considered;
- mandatory hard-sweep ledger with each family marked `zero`, `hard hit`, or `not applicable`;
- for each mandatory hard family: scan scope, actor axis, time axis, coordinate/target axis, window definition, and max-metric;
- match counts per signal and per coordinate/target axis where applicable;
- hard-supported vs soft-only classification for each match set;
- missing-MO guard: if only one location hard family has hits, re-run the other location family with the canonical query shape before submit;
- validated-zero guard: if a hard family returns zero, include the top max-metric from that same query shape;
- travel-cohort completeness: for each confirmed impossible-travel actor, the cited rows are that actor's full dense anomaly window, not only the rows that bracket a flagged adjacent jump; and any isolated single-pair travel crossing left uncited is recorded in `considered_not_cited` with its reason;
- incident-membership / cardinality check: every cluster that clears the hard gate is represented in the final refs — each sub-cluster of an evidence-connected incident AND each independent hard incident; a singular-phrased brief ("one hit") removes no hard-supported cluster from refs. Record the connecting-signal test result (e.g. cross-actor identifier collision = zero) to label same-incident vs. independent, and list only soft/threshold-only candidates in `considered_not_cited`;
- exclusion reason for any record left out; "different date", "different MO", "fewer records", or "looser window than another cluster" is never enough to exclude a hard-supported cluster — only failure of the hard gate is;
- per-record evidence map for the final cohort;
- disjoint hard sub-cluster count and temporal span;
- confirmation that no final record is supported only by a soft signal;
- final cohort count with no truncation.

The message records and `refs` records must be the same pruned hard-supported cohort.

## Outcomes

- `OUTCOME_OK`: complete hard-supported cohort or requested risk answer found and cited.
- `OUTCOME_NONE_CLARIFICATION`: the brief does not define enough scope to choose between mutually-exclusive candidate cohorts - two readings of the *same* records that cannot both be true, with no tiebreak. Multiple independent hard-supported clusters are not by themselves a clarification trigger: cite them all.
- `OUTCOME_NONE_UNSUPPORTED`: the requested risk action requires a mutation or policy not present in the runtime.
- `OUTCOME_DENIED_SECURITY`: only when the task asks to expose private customer/contact data outside the allowed boundary.

## Evidence ledger

Local placement for risk-review evidence:

`policy_docs_applied`:

- `/docs/payments/3ds.md` only when a workflow-state invariant from the 3DS
  policy shaped the hard signal.
- Other topic policies only if a future risk primitive explicitly applies their
  workflow-state invariant.

`answer_records`:

- The final hard-supported `/proc/...` cohort, one path per record marked or
  identified in the answer.
- Public customer/store/catalogue records only when the answer's evidence
  explanation relies on them.

`considered_not_cited`:

- Soft-only candidates, threshold-only bands, rejected hard-family candidates,
  false leads, and candidate clusters that did not clear the hard gate.
- Isolated two-event travel crossings that did not reach a confirmed dense
  window-cluster and were not corroborated by another hard family.
- Private contact/profile fields read for risk context but not allowed in the
  answer.

`refs_must_include`:

- Every `/proc/...` record in the final message cohort.
- Any policy doc whose workflow-state invariant actually shaped a hard signal.

`refs_must_not_include`:

- Soft-only records, truncated examples, rejected candidates, private contact
  records, or rows used only to validate a zero result. A hard-supported cluster
  is never excluded merely because the brief used singular phrasing or because
  another hard cluster is larger, tighter, or cleaner.

`post_state_records`:

- none; this BP is information-only and never mutates.

## Anti-patterns

- Narrowing the remaining hard-family scans to a customer, date, store, or device found by an earlier family when the user brief did not narrow scope.
- Submitting after the first hard cluster without completing the mandatory hard sweep.
- Recording `zero` for a hard family without a max-metric from the same query shape.
- Searching only PMF/DFP/distance columns and skipping workflow-state columns.
- Submitting a threshold-only distance band with no discrete or structural confirmation.
- Treating observed-vs-home distance as hard evidence by itself; home coordinates are coarse risk-fixture context.
- Treating a missing live basket file on an archived payment as a hard inconsistency before checking the archive flag and payment line snapshot.
- Computing impossible travel from store coordinates or other claimed target coordinates instead of observed coordinates.
- Citing only the time-adjacent rows that bracket an impossible-travel jump while dropping the same actor's other rows inside the same dense anomaly window.
- Treating an isolated two-event impossible-travel crossing as a confirmed incident when the actor shows no surrounding dense multi-location rotation and no other hard-family signal on the same actor or rows.
- Concluding "no burst" from the stationary-burst shape when the actor's dense short window has a large observed spread; that is a moving travel burst, not an absence of fraud.
- Substituting a multi-customer same-store/co-location query for the stationary single-actor multi-target burst check.
- Treating `MAX(payment_created_at) - MIN(payment_created_at)` over an actor's whole history as a dense burst window.
- Treating a new device, high amount, or one actor's long busy timeline as fraud without a hard signal.
- Treating stable observed-home plus distant store as fraud without impossible observed movement or dense single-actor multi-target burst evidence.
- Treating stable observed coordinates as soft when one actor rotates through many distinct stores, targets, or resources inside minutes.
- Sweeping only observed coordinates when a claimed target coordinate axis exists.
- Unioning a soft-only cluster into a true incident because it is nearby in time, amount, customer family, or narrative similarity.
- Dropping a fully hard-supported cluster (confirmed dense travel burst, stationary multi-target burst, identifier collision, or record/state invariant) because it is unconnected to a larger cluster, sits on a different date, uses a different MO, or has fewer records or a looser window than a competitor; under a single-hit brief the singular phrasing asserts fraud exists, it does not cap the cohort to the highest-count cluster.
- Treating every record returned by one hard-family query as one cluster; independent single-actor flags from the same family are separate incidents — each cited if it clears the hard gate — not one merged cluster.
- Dropping a hard-supported sub-cluster of the *same* evidence-connected incident because another sub-cluster is cleaner, larger, earlier, or uses a different MO.
- Dropping smaller hard-supported sub-clusters of the same incident.
- Using `LIMIT 10` or `LIMIT 20` on the query that drives the final answer.
- Treating "one hit" as one record, one actor, one date window, or a licence to cite only the single highest-count cluster.
- Inventing shared PMF/DFP, workflow, or geo evidence that was not returned by a query.

## Dependencies

> If any of these dependencies change, this BP file may have become stale and must be re-derived.

- `/docs/payments/3ds.md` - legitimate 3DS workflow-state transitions used for payment invariant checks.
- `/bin/sql` (`--help`) - SQL interface and schema-discovery contract.
- SQL table `payment_transactions` - primary risk record, fingerprints, `payment_created_at`, `payment_status`, observed coordinates (`observed_latitude` / `observed_longitude`), `is_archived_basket_reference`, and 3DS columns.
- SQL table `customer_accounts` - customer identity and home-coordinate context (`home_latitude` / `home_longitude`) for distinguishing remote shopping from observed-location fraud.
- SQL table `stores` - joined store location axis for geo anomaly checks.
- SQL table `shopping_baskets` - basket/customer/store joins and archive context.
- SQL table `shopping_basket_items` - basket resource lines (`requested_quantity`) for quantity/resource reconciliation.
- SQL table `payment_transaction_items` - line-level reconciliation (`purchased_quantity`, `item_unit_price_cents`) for amount anomalies.
- SQL table `product_variants` - catalogue price joins for amount/line checks.
- SQL table `store_inventory` - reserve/availability arithmetic and store/SKU resource axis.
- SQL table `return_requests` - return/payment/basket/customer workflow joins.
- `/proc/payments/README.md` - archived-payment semantics, observed-coordinate meaning, and opaque fingerprint semantics.
- `/proc/customers/README.md` - coarse customer home-area coordinate semantics used by risk fixtures.
- `/proc/stores/README.md` - store branch coordinate semantics for payment-risk/distance checks.
