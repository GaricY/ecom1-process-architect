# bp_dispatch_planning v0003

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-22T10:46:35+00:00`
- parent: `v0002`

## Rationale

Owning layer: domain_policy (bp_dispatch_planning). Rebased onto v0002 (extended). v0002 correctly rewrote Process step 6 to price the expected late penalty into route selection (nominal_net minus expected_late_penalty, never trade buffer/hops for small savings), which addresses the late-penalty bleed. But v0002 left step 5 minimal and so does not fix the distinct error this trial's Executor actually made: its own code comments read lane `capacity` as a hard cap on total assignments per lane ('cap 1 -> XFER-004 uses direct', 'cap 2: 3 want it, 1 must go direct') and diverted contested packages onto expensive, delay-prone direct lanes to avoid sharing — inflating transport cost AND pushing packages onto 'delays likely' lanes. /docs/dispatch.md literally says capacity is 'per trip' and packages 'share a lane' with 'scarce early capacity' ordered by priority, so this is a misreading the BP must close. A perfect expected-net calculator (v0002) still diverts if it believes a shared lane can hold only N packages total, so v0002 alone is insufficient. The extension rewrites step 5 to state the per-trip queue/priority semantics and forbid diverting to a costlier/more delay-prone route merely to dodge a lane's per-trip capacity (divert only when the expected next-trip wait would miss due_time by more than the cheaper route saves), and adds one anti-pattern naming this mistake. v0002's step 6 and its nominal-net anti-pattern are kept verbatim. Class-level rules, no task literals. Dependency description on /docs/dispatch.md restored to mention the per-trip capacity/priority queue semantics this rule operationalizes.

## Rollback

Create a new version from v0002 content if the per-trip-queue capacity-sharing guidance over-constrains route choice or harms scores; the only change versus v0002 is Process step 5 plus one anti-pattern line and the restored capacity phrase in the dispatch.md dependency.

## Dependencies
- `workspace:/docs/dispatch.md` — Source of the per-trip capacity/priority queue semantics ('capacity per trip', 'share a lane', 'scarce early capacity'), the expected-net-profit objective (margin vs trip cost vs late/missed penalties), the delay_hint model, and the output schema this BP encodes.
- `workspace:/docs/attachments.md` — Referenced in Inputs/Dependencies as the /uploads root for the request-named wave and TSV input files; if it changes, that location wording can go stale.
