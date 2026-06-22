# Fraud Risk Review

## When this process applies

Read this process for fraud, risk, anomaly, archived-payment review, "identify the fraudulent records", "mark every suspicious payment", or any plural task that asks for a complete risk cohort. It is an information/discovery BP. It does not authorize payment mutation and does not own final refs projection or submission. After finding the cohort, classify the Evidence ledger and use [refs](refs.md) and [submission_terminal](submission_terminal.md).

## Inputs

- `bin-help/sqlite_schema.txt` — the reconstructed `/proc` projection: family/field map and foreign-key edges. SQL is **unavailable** (`/bin/sql` reports the PROD cluster is down); read `/proc` JSON records directly.
- Live workspace paths: primarily `/proc/payment-ledger/`, plus `/proc/carts/`, `/proc/locations/`, `/proc/return-workflows/`, `/proc/catalog/` for joins.
- `/docs/payments/3ds.md` — legitimate 3DS state transitions for workflow-state invariants.

**Record shape.** `payment-ledger` carries `id`, `order_id`, `basket_id`, `customer_id`, `store_id`, `amount_cents`, `currency`, `status`, `created_at` (event time), `payment_method_fingerprint`, `device_fingerprint`, `observed_lat` / `observed_lon` (checkout-time risk-log coordinates, not a customer address), `lines[]` (`sku`, `quantity`, `unit_price_cents`), `three_ds` (`status`, `attempts`, `max_attempts`, `retry_after`, `failure_reason`), and `archived` (boolean). There is **no** customer-account record and no customer home coordinate in this world — distance-from-home is not an available axis. `locations` carries branch `lat`/`lon` for store-distance context. Read the current field list from the schema before composing a scan.

## Process

1. Define the task scope first: archived payments only, one store, one day, one customer, one campaign, or whatever the brief names. Record the scope predicate and universe size in scratchpad. Load the in-scope records once with `ws.find`/`ws.read` into `state` and aggregate in Python.
2. The analysis scope is the user's predicate, not a suspect found mid-analysis. A customer, day, store, device, or identifier surfaced by one family is a candidate cluster only; it must not narrow the remaining hard-family scans.
3. Read the full field list for the in-scope family from the schema. Do not look only at fields whose names sound like "fraud". Identify the actor, event-time, observed-location, claimed-target, exact-identifier, resource, and workflow-state fields that exist.
4. Run the **mandatory hard sweep** and record each family as `zero`, `hard hit`, or `not applicable` (required field absent):
   - cross-actor exact-identifier collisions: same `payment_method_fingerprint`, same `device_fingerprint`, repeated `basket_id`/`order_id`, or identical `created_at` across different `customer_id`s;
   - workflow-state invariants: `status == paid` rows carrying a failed/pending `three_ds`, exhausted attempts, or impossible transitions under `/docs/payments/3ds.md`;
   - record invariants: `amount_cents` vs `Σ(lines.quantity × unit_price_cents)`, `archived` flag consistency, payment↔cart↔return joins, inventory/reserve arithmetic (`locations.inventory` `on_hand`/`reserved`), duplicate payments. A missing live cart file on an `archived` payment is not a hard mismatch by itself — use the payment's `lines` snapshot;
   - impossible observed travel: consecutive events by the same `customer_id` whose `observed_lat`/`observed_lon` move impossibly far for the elapsed time;
   - stationary single-actor multi-target burst: one `customer_id` with many events at many distinct `store_id`s (or targets/resources) within minutes while observed coordinates stay nearly stationary.
5. For every family, the ledger records the scan shape, not just the result: scan scope, actor axis, time axis, coordinate/target axis, window definition, and the max-metric used to validate a zero.
6. Finding one hard cluster is not enough. Continue until every family above has a recorded result and trustworthy scan shape.
7. Classify candidate matches before building the cohort:
   - hard-supported: exact-identifier collision across actors, impossible observed travel, stationary single-actor multi-target burst, workflow-state invariant, or record invariant;
   - soft-only: one new device/payment fingerprint for one actor, high amount, high purchase count, a distant observed-vs-store band, a long busy timeline, or any smooth threshold band with no structural confirmation.
8. Only hard-supported records enter the final cohort. Soft-only records are excluded by default, even when they look suspicious or sit near a true incident window.
9. Location/target scan shapes stay separate:
   - impossible observed travel is observed-to-observed across all actors in scope: group by `customer_id`, order by `created_at`, compare consecutive `observed_lat`/`observed_lon`, compute elapsed minutes;
   - do not compute impossible travel from store coordinates. Fast rotation through distant stores with stable observed coordinates is a burst/tempo anomaly, not observed travel;
   - stationary single-actor burst is grouped by one `customer_id` (not by store, not across customers). The window is a dense sub-window from each event, not `MAX(created_at) - MIN(created_at)` over the actor's whole history. Count events and distinct `store_id`s; confirm the observed-coordinate spread inside the window is small; expand a hit to all in-window records for that actor.
10. Stable observed coordinates are not automatically soft. Stable observed plus distant stores at ordinary cadence is remote-shopping context; stable observed plus many distinct stores/targets within minutes is a hard tempo anomaly. The discriminator is short-window target rotation, not observed-to-store distance.
11. When a hard family returns zero, validate the negative: record the top max-metric for that family (largest same-actor observed jump/speed for travel; largest same-actor short-window distinct-target count and observed spread for burst). If the max-metric contradicts the zero, fix the scan.
12. For high-count fuzzy signals, regroup by `(customer_id, short_time_window)` before discarding as noise — a broad legitimate tail can hide a dense hard-supported burst, but the broad tail is cited only if it passes the hard gate.
13. Include every member of inseparable hard evidence groups. If a hard signal flags a pair or duplicate group and the data does not identify the sole offender, both members belong in the cohort.
14. The final cohort is the union of every hard-supported cluster in scope. Different hard families may identify different sub-clusters; do not submit only the first/largest/cleanest while another hard family has nonzero matches.
15. Interpret "one hit" / "one incident" as one evidence-connected campaign, not one pure date window. Different date or MO is not enough to exclude a hard-supported cluster unless the brief narrows scope.
16. Build a per-record evidence map before refs: each cited record has a path, hard-signal name, condition, and cluster id. Remove any record justified only by narrative, a threshold, or temporal proximity.
17. Run the final cohort enumeration without truncation and confirm it is complete.

## Risk primitives (compute over `/proc`, not SQL)

For new risk angles (delivery, reservation, refund, inventory, non-3DS payment), first map the schema into these axes, then apply the hard primitives:

- actor axis: `customer_id`, `device_fingerprint`, `payment_method_fingerprint`;
- claimed-target axis: `store_id`, basket/order, inventory store, or other named resource owner;
- event-time axis: `created_at` (payment), return/created times, or workflow-transition time;
- resource axis: `sku`, basket, payment, return, inventory row;
- invariant axis: amount/lines, payment↔cart↔return joins, inventory/reserve arithmetic, and workflow state under `/docs/payments/3ds.md`.

Hard primitives: impossible observed movement for one actor; too many claimed targets/resources in a short sub-window for one actor; exact-identifier collision across actors; ledger reconciliation across families; policy/workflow-state invariant. Compute travel and burst with per-actor sequencing/sliding windows in Python over the loaded records.

## Coverage check before ledger/submission

Scratchpad must show: scope predicate + universe size; full field list considered; the mandatory hard-sweep ledger (each family `zero`/`hard hit`/`not applicable`); per family the scan scope, actor/time/coordinate/target axis, window, and max-metric; match counts; hard-vs-soft classification; missing-MO guard (if only one location family hit, re-run the other); validated-zero guard (top max-metric on zeros); hard-hit union check; exclusion reason for any hard hit left out; per-record evidence map; disjoint sub-cluster count + temporal span; confirmation no final record is soft-only; final cohort count with no truncation. The message records and `refs` records must be the same pruned hard-supported union.

## Outcomes

- `OUTCOME_OK`: complete hard-supported cohort or requested risk answer found and cited.
- `OUTCOME_NONE_CLARIFICATION`: the brief does not define enough scope to choose between plausible hard-supported cohorts.
- `OUTCOME_NONE_UNSUPPORTED`: the requested risk action needs a mutation or policy not present in the runtime.
- `OUTCOME_DENIED_SECURITY`: only when the task asks to expose private contact data outside the allowed boundary.

## Evidence ledger

`policy_docs_applied`:

- `/docs/payments/3ds.md` only when a 3DS workflow-state invariant shaped a hard signal.

`answer_records`:

- The final hard-supported `/proc/...` cohort, one live path per record marked or identified.
- Public store/catalogue records only when the evidence explanation relies on them.

`considered_not_cited`:

- Soft-only candidates, threshold bands, rejected hard-family candidates, false leads, and clusters outside the final union.

`refs_must_include`:

- Every `/proc/...` record in the final message cohort, and any policy doc whose invariant shaped a hard signal.

`refs_must_not_include`:

- Soft-only records, rejected candidates, staff contact records, or rows used only to validate a zero.

`post_state_records`:

- none; this BP never mutates.

## Anti-patterns

- Narrowing remaining hard-family scans to a customer/day/store/device found by an earlier family when the brief did not narrow scope.
- Submitting after the first hard cluster without completing the sweep.
- Recording `zero` without a max-metric from the same scan shape.
- Searching only fingerprint columns and skipping workflow-state fields.
- Computing impossible travel from store coordinates instead of `observed_lat`/`observed_lon`.
- Treating a missing live cart file on an `archived` payment as a hard inconsistency before checking the flag and the payment `lines` snapshot.
- Substituting a multi-customer same-store query for the stationary single-actor multi-target burst check, or using whole-history `MAX-MIN(created_at)` as a dense burst window.
- Treating a new device, high amount, or long busy timeline as fraud without a hard signal.
- Inventing a distance-from-customer-home axis — no customer home coordinate exists in this world.
- Dropping a nonzero hard-supported cluster because another is cleaner/larger, or dropping smaller hard sub-clusters of the same incident.
- Truncating the final cohort enumeration.

## Dependencies

> If any of these dependencies change, this BP file may have become stale and must be re-derived.

- `/docs/payments/3ds.md` — legitimate 3DS workflow-state transitions used for payment invariant checks.
- `payment-ledger` (`/proc/payment-ledger`) — primary risk record: fingerprints, `created_at`, `status`, `observed_lat`/`observed_lon`, `amount_cents`, `lines`, `three_ds`, `archived`, and the `customer_id`/`store_id`/`basket_id` join keys.
- `carts` (`/proc/carts`) — basket/customer/store joins and archive context.
- `locations` (`/proc/locations`) — branch `lat`/`lon` and `inventory` (`on_hand`/`reserved`) for store-distance and reserve arithmetic.
- `return-workflows` (`/proc/return-workflows`) — return/payment workflow joins.
- `catalog` (`/proc/catalog`) — `price_cents` for amount/line reconciliation.
