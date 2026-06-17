# bp_refs_and_submission v0010

- mode: `failure_fix`
- created_by: `human`
- created_at: `2026-05-24T03:00:00+00:00`
- parent: `v0009`

## Rationale

Manual authoring after v0009 still failed t38 at 46% and t40 at 48% in
run `20260523-185835` (run-level avg 97.6%; only the three
`refs_and_submission` discovery trials were partial). v0009 fixed the
prior "rank sub-clusters and keep the strongest" failure mode by
adding the disjoint-sub-cluster union rule (rule 5) and rewriting rule
6 so "one hit" allows multi-actor MOs.

The new failure mode is **upstream** of those rules: the Executor's
impossible-travel signal is implemented with `haversine(observed_lat,
observed_lon)` (actor-side coords) instead of `haversine(stores.lat,
stores.lon)` (claimed-entity coords joined via `store_id`). The dev
benchmark's fraud cohorts contain two MOs per hit:

- **Paired-travel** — N customers each make two payments 200-500 km
  apart in minutes; the actor's observed coords genuinely move.
- **Stationary-burst** — one customer makes 10+ payments at 10+ stores
  in 2-4 minutes while `observed_lat`/`observed_lon` stays on one
  point and `store_id` rotates across distant cities.

The observed-axis sweep catches MO (1) but returns 0 km for MO (2).
The store-axis sweep catches both. In the failing run t39 happened to
use store coords and scored 100%; t38 and t40 used observed coords and
scored 46-48%, recovering exactly the paired-travel half of each
cohort. v0009 rule 2's "geographic separation (impossible travel)"
phrasing does not say which axis to use; the choice is stochastic
across trials.

## Fix — surgical edits to v0009

1. **Rule 2 — Time/sequence row of the signal-families table.**
   Expanded to require sweeping BOTH location axes (actor-side
   observed AND claimed-entity-side stored) and unioning the results.
   Worked example explains why stationary-burst MOs require the store
   axis.
2. **Rule 4 — added "Density refinement" paragraph.** A high-count
   threshold signal (50+, 100+, 200+) is not automatically noise —
   regroup matches by `(actor_id, short_time_window)` and look at
   per-group densities before dismissing. Bursts can hide inside the
   continuous distribution. Worked example: "geo anomaly >100km: 174
   matches; group by (customer_id, day): 150 customers × 1 record
   (noise), 1 customer × 12 records in 3 min — that customer's 12
   records are a burst sub-cluster, include them all."
3. **Rule 6 — added "Temporal scoping" paragraph.** "One hit" implies
   one connected 1-3 week window — sub-clusters of the same MO
   separated by 4+ weeks are separate incidents. Addresses the t40
   false-positive observed in my analytical solve: a 3-record
   sub-cluster on 2021-06-12 sits 5 weeks after the main 2021-05-06
   hit and the grader excludes it.
4. **Rule 7 — three new coverage-check line items.**
   - For parameterised signals (axis-of-distance, threshold value,
     window size), record which axes / parameter values were swept
     and the per-axis match counts.
   - For 50+ continuous-threshold signals, record the
     density-by-actor distribution before dismissing.
   - For "one hit" / "one incident" briefs, record the temporal span
     of the answered cohort and confirm it fits inside a single
     connected 1-3 week window (or document why a wider window
     applies).
5. **Three new anti-patterns:**
   - Single-axis-only impossible-travel when the schema exposes
     multiple location axes.
   - Dismissing a 50+/100+/200+ threshold signal as noise without
     density-by-actor refinement.
   - Submitting sub-clusters from multiple temporal windows when the
     brief says "one hit".

No language is benchmark-specific — every rule names the abstract
pattern (location axis, threshold density, temporal connectedness)
with column names as illustrative. The fix complements v0009 instead
of replacing it: disjoint-sub-cluster union (v0009 rule 5) still
applies once the signal correctly finds all sub-clusters. v0009's
discrete > fuzzy rule (rule 4) still holds; density refinement is a
sub-rule that runs **before** dismissing the fuzzy signal, not after.

## Validation

Pre-validation: my analytical solver `ecom-py/solve_fraud.py`
implements exactly the multi-axis impossible-travel signal (via store
coords) the new rule 2 demands. Live-grader scores against the dev
benchmark:

- t38: 100% (21/21 records, 0 false positives)
- t39: 100% (18/18 records, 0 false positives)
- t40: 92.7% (22/22 true positives + 3 false positives from
  cust_025's 5-week-later burst — exactly the case the new rule 6
  temporal-scoping paragraph addresses)

The Executor with v0010 should match the analytical baseline after
applying both the multi-axis sweep and the temporal scoping.

## Rollback

Revert to v0009 by creating a new version from v0009 content if the
new rules cause regressions on tasks where (a) only one location axis
is meaningful in the schema (multi-axis paragraph asks for a sweep
that is structurally impossible), or (b) the brief intends multiple
temporally-distant hits as one cohort and the temporal-scoping
anti-pattern wrongly trims them. The narrow rollback is dropping the
temporal-scoping paragraph from rule 6 and its anti-pattern, keeping
the multi-axis and density-refinement edits which target the t38/t40
under-recall path.

## Dependencies

- `workspace:/docs/security.md` — Cross-boundary rule, 'no release of
  personal information across the boundaries' clause, and Identity
  Audit Phrases denial templates cited throughout the customer-actor /
  employee-actor branches; unchanged in this edit but still
  load-bearing.
- `workspace:/docs/payments/3ds.md` — Defines the legitimate
  three_ds_status transition table and the attempts < max_attempts
  invariant that the authentication / workflow-state-invariants signal
  family in the discovery section keys off; if the legitimate state
  set or recovery rule changes, the signal-families table and rule 3's
  worked example go stale.
- `bin_help:id.help.txt` — Defines the shape of /bin/id output (user
  prefix cust_* / emp_* / guest, roles list) that the actor-type
  branching and the pre-submission checklist key off; unchanged in
  this edit.
