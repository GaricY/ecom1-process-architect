# Fraud Risk Review

## When this process applies

Read this process for fraud, risk, anomaly, Risk-Ops, archived-payment review, "identify the fraudulent records", "mark every suspicious payment", or any plural task that asks for a complete risk cohort. It is an information/discovery BP. It does not authorize payment mutation and does not own final refs or submission.

After finding the cohort, use [refs](refs.md) for citations and [submission_terminal](submission_terminal.md) to submit.

## Inputs

- `bin-help/sqlite_schema.txt` — the recovered record-shape map for the `/proc` families and the field names below.
- Live `/proc` families read with `/bin/jq` / `/bin/cat`: `/proc/payment-ledger` (payments), `/proc/carts`, `/proc/return-workflows`, `/proc/locations` (+ `location_inventory`), `/proc/catalog`, `/proc/staff`. **`/bin/sql` is unavailable** — see [os_tooling_incidents](os_tooling_incidents.md); build indexes in `execute_python` over the JSON you read (stdlib `json`, `datetime`, `defaultdict`, `Counter`, `math`).
- `/docs/payments/3ds.md` — legitimate 3DS state transitions for workflow-state invariants.

**Schema note (renamed projection).** Payment risk fields are now `payment_ledger.created_at` (event time), `observed_lat` / `observed_lon` (checkout-time risk-log coordinates, not customer address), `archived` (archive flag; archived payments may omit `order_id` / `basket_id`), `status` (`paid` / `requires_3ds_action`), plus the opaque exact identifiers `payment_method_fingerprint` / `device_fingerprint`. 3DS fields live in the `payment_three_ds` shape (`status`, `attempts`, `max_attempts`, `retry_after`, `failure_reason`). **There is no customer account family** in the live projection — `home_latitude` / `home_longitude` no longer exist, so observed-vs-home distance is not an available axis. Store coordinates (`locations.lat` / `locations.lon`) remain for branch-distance context. Read the current field list from `bin-help/sqlite_schema.txt` before composing a scan.

## Process

1. Define the task scope first: archived payments only, one store, one day, one customer, one campaign, or whatever the brief names. Record the scope predicate and universe size in scratchpad.
2. The analysis scope is the user's predicate, not a suspect found mid-analysis. A customer, date, store, device, or identifier surfaced by one family is a candidate cluster only; it must not narrow the remaining hard-family scans.
3. Read the full field list for the in-scope family from `bin-help/sqlite_schema.txt`. Identify the actor, event time, observed location, claimed target, exact identifier, resource, and workflow-state fields that exist. Do not search only fields whose names sound like "fraud".
4. Before choosing an answer, run the mandatory hard sweep and record each family as `zero`, `hard hit`, or `not applicable` (required fields absent):
   - cross-actor exact identifier collisions: shared `payment_method_fingerprint`, shared `device_fingerprint`, repeated baskets, identical timestamps, or other exact values across actors;
   - workflow-state invariants: `paid` rows carrying failed/pending 3DS state, exhausted attempts, or impossible transitions under `/docs/payments/3ds.md`;
   - record/family invariants: amount vs lines/products, archive flags, payment vs cart/store joins, inventory/reserve arithmetic, return/payment joins, duplicate payments. A missing live cart file on an archived payment is not a hard mismatch by itself — use the payment's own `lines` snapshot;
   - impossible observed travel: sequential events by the same actor whose `observed_lat` / `observed_lon` move impossibly far for the elapsed time;
   - stationary single-actor multi-target burst: one actor with many events at many distinct stores/targets within minutes while observed coordinates stay nearly stationary.
5. For every hard-sweep family, the ledger must record the scan shape, not only the result: scan scope, actor axis, time axis, coordinate/target axis, window definition, and the max-metric used to validate zero results.
6. Finding one hard-supported cluster is not enough. Continue until every family above has a recorded result and trustworthy scan shape.
7. Classify candidate match sets before building the cohort:
   - hard-supported: exact identifier collision across actors, impossible observed travel, stationary single-actor multi-target burst, workflow-state invariant, or record/family invariant;
   - soft-only: one new device/payment fingerprint for one actor, high amount, high purchase count, distant observed-vs-store band, long busy timeline, or any smooth threshold band with no structural confirmation.
8. Only hard-supported records enter the final cohort. Soft-only records are excluded by default, even when high value or near a true incident window.
9. Keep location scan shapes separate:
   - impossible observed travel is an observed-to-observed check across all in-scope actors: partition by actor, order by `created_at`, compare consecutive `observed_lat`/`observed_lon`, compute elapsed minutes;
   - do not compute travel from store or other claimed-target coordinates. Fast rotation through distant stores with stable observed coordinates is a burst/tempo anomaly, not travel;
   - stationary single-actor burst groups by one actor, in a dense sub-window (not `max(created_at) - min(created_at)` over the actor's whole history); count events and distinct stores/targets, confirm observed-coordinate spread inside the window is small, and expand a hard hit to all in-window records for that actor.
10. Stable observed coordinates are not automatically soft. Stable observed plus distant store at ordinary cadence is remote-shopping context; stable observed plus many distinct stores/targets within minutes is a hard tempo anomaly. The discriminator is short-window target rotation.
11. When a hard family returns zero, validate the negative: record the top max-metric from the same scan shape (largest same-actor observed jump for travel; largest short-window distinct-store count and observed spread for burst). If the max-metric contradicts the zero, fix the scan before trusting the ledger.
12. For high-count fuzzy signals, regroup by `(actor_id, short_time_window)` before discarding as noise. A broad legitimate tail can hide a dense hard-supported burst, but the tail itself is not cited unless it passes the hard gate.
13. Include every member of inseparable hard evidence groups (e.g. both sides of a shared-fingerprint pair when the data does not single out the offender).
14. After the hard gate, the final cohort is the union of every hard-supported cluster in scope. Different hard families may identify different sub-clusters; do not submit only the first/largest/cleanest cluster while another hard family has nonzero matches.
15. Interpret "one hit" / "one incident" as one evidence-connected campaign, not one pure date window.
16. Build a per-record evidence map before refs: path, hard signal name, condition, cluster id. Remove any record justified only by narrative, threshold, or temporal proximity.
17. Run the final cohort scan over the whole in-scope universe (no truncation) and confirm completeness.

## Risk primitives (adapt to the JSON projection)

Use these as scan-shape references, not fixed thresholds. There is no SQL engine — read the relevant `/proc` JSON via `/bin/jq` / `/bin/cat` and compute in `execute_python`.

- **Observed travel:** per actor, order their payments by `created_at`; for consecutive events compute elapsed minutes and the observed-coordinate jump (`abs(observed_lat - prev) + abs(observed_lon - prev)`); flag short-elapsed large-jump pairs. Validate a zero with the largest same-actor jump in scope.
- **Stationary multi-target burst:** per actor, slide a short window (e.g. ≤5 minutes) from each event; count events and distinct `store_id`; confirm the observed-coordinate spread in the window is small. Flag dense windows; expand a hit to all in-window records for that actor.
- **General axes** for new angles (delivery, reservation, refund, inventory, non-3DS payment): map the schema into actor / claimed-target / event-time / resource / invariant axes, then apply the same hard primitives (impossible observed movement, too many targets in a short window for one actor, exact identifier collision across actors, ledger reconciliation across families, workflow-state invariant under the relevant `/docs/...` policy). `location_inventory`, `cart_lines`, and `return_workflows` are current examples for resource/invariant checks.

## Coverage check before refs/submission

Scratchpad must show: scope predicate and universe size; full field list considered; mandatory hard-sweep ledger (each family `zero` / `hard hit` / `not applicable`); per-family scan scope, axes, window, and max-metric; match counts per signal; hard-vs-soft classification per match set; missing-MO guard (if only one location family has hits, re-run the other with the canonical shape); validated-zero guard (top max-metric on every zero); hard-hit union check; exclusion reason for any hard hit left out ("different date"/"different MO" is not enough unless the brief narrowed scope); per-record evidence map; disjoint sub-cluster count and span; confirmation no final record is soft-only; final cohort count with no truncation.

The message records and `refs` records must be the same pruned hard-supported union.

## Outcomes

- `OUTCOME_OK`: complete hard-supported cohort or requested risk answer found and cited.
- `OUTCOME_NONE_CLARIFICATION`: the brief does not define enough scope to choose between multiple plausible hard-supported cohorts.
- `OUTCOME_NONE_UNSUPPORTED`: the requested risk action requires a mutation or capability the runtime does not support.
- `OUTCOME_DENIED_SECURITY`: only when the task asks to expose private contact data outside the allowed boundary.

## Refs to set in scratchpad

- Every `/proc/...` record marked in the answer (its live path).
- `/docs/payments/3ds.md` if a 3DS workflow-state invariant was applied.
- Public store/catalogue records only when the evidence explanation relies on them.
- Then run [refs](refs.md) for final citation safety.

## Anti-patterns

- Narrowing remaining hard-family scans to a suspect found by an earlier family when the brief did not narrow scope.
- Submitting after the first hard cluster without completing the mandatory hard sweep.
- Recording `zero` for a hard family without a max-metric from the same scan shape.
- Searching only fingerprint/distance fields and skipping workflow-state fields.
- Submitting a threshold-only band with no structural confirmation.
- Treating observed-vs-store distance as hard evidence by itself.
- Computing impossible travel from store coordinates instead of observed coordinates.
- Treating `max(created_at) - min(created_at)` over an actor's whole history as a dense burst window.
- Treating a new device, high amount, or a long busy timeline as fraud without a hard signal.
- Treating a missing live cart file on an archived payment as a hard inconsistency before checking the `archived` flag and the payment `lines` snapshot.
- Dropping a nonzero hard-supported cluster because another is cleaner/larger/earlier or uses a different MO.
- Capping the final cohort scan.
- Inventing shared fingerprint / workflow / geo evidence not produced by an actual scan.
- Trying `/bin/sql` (it is down) or assuming a customer home-coordinate axis exists (no customer account family).

## Dependencies

> If any of these dependencies change, this BP file may have become stale and must be re-derived.

- `/docs/payments/3ds.md` — legitimate 3DS workflow-state transitions used for payment invariant checks.
- `bin-help/sqlite_schema.txt` — the recovered record-shape map and field names for all risk families (replaces `/bin/sql` schema discovery and the removed `/proc/*/README.md` semantics).
- `bin-help/jq.help.txt`, `bin-help/cat.help.txt` — JSON read tools used for the scans now that `/bin/sql` is unavailable.
- `sql_table payment_ledger` — primary risk record: fingerprints, `created_at`, `status`, `observed_lat`/`observed_lon`, `archived`.
- `sql_table payment_three_ds` — `status`/`attempts`/`max_attempts`/`retry_after` for workflow-state invariants.
- `sql_table payment_lines` — line-level reconciliation (`quantity`, `unit_price_cents`) for amount anomalies.
- `sql_table carts` / `sql_table cart_lines` — cart/customer/store joins and resource lines.
- `sql_table return_workflows` — return/payment workflow joins.
- `sql_table locations` / `sql_table location_inventory` — store coordinates and reserve/availability arithmetic.
- `sql_table catalog` — price joins for amount/line checks.
