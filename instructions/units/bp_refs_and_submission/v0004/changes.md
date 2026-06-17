# bp_refs_and_submission v0004

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-05-21T11:53:42+00:00`
- parent: `v0003`

## Rationale

Executor failed a discovery / identify-all task with 23.2% score (5 of 21 fraud records recovered). The task asked the actor to enumerate every fraudulent archived payment record. The Executor found one anomaly signal (impossible-travel pairs on a single day, yielding 10 candidate records), then narrowed to 5 records (one 'guilty half' per pair) and submitted. Two compounding failure modes: (a) stopped at the first matching signal and never enumerated the other obvious anomaly families that the schema supports (e.g. observed_lat/lon vs the joined stores.lat/lon — Snippet 15 found that signal but the Executor abandoned it; record-internal invariants; cross-table joins to public records), and (b) halved an inseparable evidence pair on the assumption that only one member of each impossible-travel pair was fraudulent, when the evidence on its own does not distinguish offender from cloned counterpart. The existing OUTCOME_OK discipline section talked only about lookup tasks (cite-path discipline) and did not address enumeration coverage. Fix: add a 'Discovery / identify-all task discipline' section that (1) defines when the rule fires (plural-enumerative wording with no explicit count), (2) requires the answer to be the complete set within the task-scoped universe, (3) lists the signal families to enumerate (record-internal, cross-record duplicates, cross-table joins, time/sequence) using schema column names as illustrative examples, (4) mandates including every member of an inseparable evidence group, (5) reframes 'one hit' / 'one event' wording as a cluster-shape descriptor not a record count, and (6) adds a coverage check (scope universe, signal log, two-signal-minimum) into the pre-submission snippet. Cross-links from OUTCOME_OK discipline and What-to-include-in-refs. Three new anti-patterns capture the exact failure modes (stopping at first signal, halving an evidence pair, misreading 'one hit' as a count). Generalises across fraud / quality / anomaly reviews of any /proc/<family>, not just payments.

## Rollback

Create a new version from v0003 content if the Discovery / identify-all discipline over-broadens answers on future trials (e.g. the grader flags answers that include genuine records alongside fraudulent ones because the executor refused to narrow an evidence pair when narrowing was the correct call).

## Dependencies
- `workspace:/docs/security.md` — Authoritative source for the cross-boundary rule, ownership rule, and Identity Audit Phrases the denial wording draws from; actor-type / ownership branching cites this doc directly.
- `workspace:/docs/README.md` — Document Families split decides which /docs/* are active decision policies eligible for refs vs operational background excluded from refs; the 'What to include / NOT to include' sections key off this taxonomy.
- `bin_help:id.help.txt` — Defines the shape of ws.id() output (cust_* vs emp_* prefix, roles list) that the actor-type branching and pre-submission checklist key off.
- `bin_help:sqlite_schema.txt` — The new Discovery / identify-all section cites schema column names (payment_method_fingerprint, device_fingerprint, observed_lat, observed_lon, basket_archived, amount_cents, unit_price_cents, customer_id, store_id, created_at) as illustrative signal families. If the warehouse schema renames or drops these columns the examples become stale and the section must be re-derived.
