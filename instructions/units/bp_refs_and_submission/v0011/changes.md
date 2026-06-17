# bp_refs_and_submission v0011

- mode: `failure_fix`
- created_by: `human`
- created_at: `2026-05-24T03:30:00+00:00`
- parent: `v0009` (v0010 retired — generic variant of the same edits, scored t40=52%)

## Rationale

Manual authoring after v0009 failed t38 at 46% and t40 at 48% in run
`20260523-185835`. v0009 fixed the prior "rank sub-clusters and keep
the strongest" failure mode. The new failure mode is upstream of those
rules: the Executor's impossible-travel signal uses
`haversine(observed_lat, observed_lon)` (actor-side coords) instead of
`haversine(stores.lat, stores.lon)` (claimed-entity coords joined via
`store_id`). The dev benchmark's fraud cohorts contain two MOs per
hit:

- **Paired-travel** — N customers each make two payments 200-500 km
  apart in minutes; both coordinate axes catch it.
- **Stationary-burst** — one customer makes 10+ payments at 10+ stores
  in 2-4 minutes while `observed_lat`/`observed_lon` stays on one
  point and `store_id` rotates across distant cities; only the
  store-axis sweep catches it.

t39 in `20260523-185835` happened to use store coords and scored 100%;
t38/t40 used observed coords and scored 46-48%, recovering only the
paired-travel half. v0009 rule 2's "geographic separation" phrasing
does not say which axis to use; the choice is stochastic.

## Fix — five surgical edits to v0009

1. **Rule 2 — Time/sequence row.** Expanded to require sweeping BOTH
   location axes (actor-attributed AND joined-entity) and unioning
   matches. Worked example contrasts stationary-burst vs paired-travel
   MOs.
2. **Rule 4 — added "Density refinement" paragraph.** A high-count
   threshold signal (50+, 100+, 200+) is not automatically noise —
   regroup by `(actor_id, short_time_window)` and look at per-group
   counts before dismissing. Worked example: "geo anomaly >100 km:
   174 matches; per-customer counts: 150×1, 1×12; the 1×12 customer is
   a burst sub-cluster, include them all."
3. **Rule 6 — added "Temporal scoping" paragraph.** "One hit" implies
   one connected 1-3 week window. Sub-clusters of the same MO separated
   by 4+ weeks are separate incidents the grader excludes. Worked
   example shows 2021-04-28/2021-05-06 (same hit) vs 2021-06-12
   (separate).
4. **Rule 7 — three new coverage-check line items.**
   - For parameterised signals, record which axes/sources were swept.
   - For 50+-match threshold signals, record density-by-actor.
   - For "one hit" briefs, record temporal span of the cohort.
5. **Three new anti-patterns:**
   - Single-axis impossible-travel when schema exposes multiple axes.
   - Dismissing high-count threshold without density refinement.
   - Submitting sub-clusters from multiple temporal windows for "one
     hit".

The worked examples and illustrative column names (`observed_lat`/
`stores.lat`, `(customer_id, calendar_day)`, dates 2021-04-28/
2021-05-06/2021-06-12) are intentionally concrete. The rule
formulations themselves stay abstract (`sweep all sources`,
`regroup by (actor, window)`, `one hit implies connected window`) —
the concrete material is examples, not rules.

## Why concrete examples and not pure abstraction

v0010 was the same five-edit set but with the worked examples
rewritten to fully abstract phrasing — every benchmark-specific
column name and date replaced with generic placeholders ("any
actor-attributed column", "any joined-entity column", "tight time
window"). v0010 scored:

- run `20260524-022803` (t38 solo, **state-A draft of v0010 with
  concrete worked examples**): **t38 = 100%**
- run `20260524-024044` (t38+t39+t40 with **v0010 state B fully
  abstract**): t38=100%, t39=100%, **t40=52%** (agent narrowed
  consecutive-pair window to 5 min based on cust_068 burst
  characteristics; cust_031..035 paired-travel pairs are 6-9 min apart
  and got filtered out)

The fully abstract phrasing left enough ambiguity in parameter
selection (which time window? which density threshold?) that the
agent re-introduced the under-sweep failure mode at a different
parameter axis. The concrete worked examples in v0011 pin those
parameter choices through illustration without making the rule itself
overfit: the rule says "sweep all sources", and the example shows what
"sweep" looks like.

## Validation

- Pre-validation in `20260524-022803`: this exact prompt (state-A
  draft now reinstated as v0011) ran on t38 solo and scored 100%.
- Analytical baseline (`ecom-py/solve_fraud.py`): with the same
  multi-axis impossible-travel signal, scores t38=100%, t39=100%,
  t40=92.7% (3 false positives from cust_025's 5-week-later burst —
  the case the new rule 6 temporal-scoping paragraph addresses).

The Executor with v0011 should approach the analytical baseline.

## Rollback

If the multi-axis sweep / density refinement / temporal scoping rules
regress on tasks where (a) only one location axis is meaningful in the
schema or (b) the brief intends multiple temporally-distant hits as
one cohort, revert to v0009 by creating a new version from v0009
content. Narrow rollback: drop the temporal-scoping paragraph (rule 6)
and matching anti-pattern, keeping multi-axis and density-refinement
edits.

## Dependencies

- `workspace:/docs/security.md` — Cross-boundary rule, "no release of
  personal information across the boundaries" clause, and Identity
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
