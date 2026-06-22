# bp_dispatch_planning v0004

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-22T12:06:34+00:00`
- parent: `v0003`

## Rationale

domain_policy failure. The Executor delivered all 10 packages (0 late, 0 missed, 0 invalid), so the entire 18% efficiency gap is avoidable transport cost. The grader charges transport cost per *trip*, not per package: one trip on a lane carries up to its `capacity` packages for a single `cost_cents`, so the plan cost is `Σ over used lanes of ceil(pkgs/capacity) × cost_cents` (this reproduces the graded EUR 39.76 = 3976 cents exactly). But Process step 6 defined `Nominal net = margin − Σ lane cost`, charging each lane's full cost to every package. That per-package model overstates multi-hop hub routes, so the Executor bought two expensive dedicated direct lanes (full `cost_cents` paid alone) instead of consolidating those packages onto hub lanes other assignments already ride at near-zero marginal cost. This also reveals that v0002's hop caution ('prefer the route with the fewest, lowest-risk lanes; do not add a hop to shave trip cost') was load-bearing in the wrong direction here — the Executor cited it verbatim to justify the direct lanes. The fix rewrites step 6 to state the per-trip shared-cost model and a total-wave expected-net objective, reframes the hop caution so extra hops cost expected late penalty (delay risk) not nominal trip cost, and replaces the nominal-net anti-pattern with a per-trip-cost one. I am narrowing the regressing v0002 wording rather than stacking a new patch; v0002's genuine lesson (don't trade buffer/route through high-delay lanes to save cost) and v0003's per-trip-capacity queue rule are preserved. The refs and terminal payload were accepted, so this is neither refs_safety nor terminal_protocol.

## Rollback

Create a new version from v0003 content if the per-trip shared-cost model and consolidation preference over-constrain route choice or harm scores; the only change versus v0003 is Process step 6 plus the two reworked anti-pattern lines and the restored trip-cost phrase in the dispatch.md dependency.

## Dependencies
- `workspace:/docs/dispatch.md` — Source of the per-trip (shared-capacity) trip-cost model, the capacity/priority queue semantics, the expected-net-profit objective (margin vs trip cost vs late/missed penalties), the delay_hint model, and the output JSON schema this BP encodes; if its cost/capacity model changes, step 6 goes stale.
- `workspace:/docs/attachments.md` — Defines /uploads as the upload root cited in Inputs for the request-named wave and TSV input files; if that location wording changes the Inputs guidance goes stale.
