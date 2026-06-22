# bp_dispatch_planning v0002

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-22T06:28:56+00:00`
- parent: `v0001`

## Rationale

domain_policy failure. The Executor delivered all 10 packages (0 missed, 0 invalid) but scored only 82.2% efficiency, bleeding EUR 22.48 in late penalties (~1.3 packages late on average). Root cause: it ranked routes by NOMINAL net (margin - cost at face-value ETA) and used delay_hint only as a weak tertiary tie-breaker, so it repeatedly took cheaper multi-hop hub routes for trivial cost savings while sacrificing schedule buffer and compounding delay risk across more lanes (e.g. a high-margin package routed three hops to save a couple hundred cents, and a thin-buffer package routed through a 'delays likely' lane). v0001 said 'maximize expected net profit' and 'use delay_hint' but gave no concrete rule for pricing the late penalty into route choice, so the Executor defaulted to nominal-net maximization. The fix rewrites Process step 6 into an explicit expected-net selection rule (score routes by nominal_net minus expected_late_penalty; never trade schedule buffer or extra hops for small cost savings, especially on high-margin packages; minimize expected lateness when no on-time route exists) and adds one anti-pattern naming the nominal-net mistake. This is the unit's first failure (v0001, world_refresh) so it is not stacking on a regressing PA rule. The terminal payload shape was accepted (OUTCOME_OK, valid JSON), so this is not a terminal_protocol or refs_safety issue.

## Rollback

Create a new version from v0001 content if the expected-net selection rule over-constrains route choice or harms scores; the only behavioural change is in Process step 6 plus one anti-pattern line.

## Dependencies
- `workspace:/docs/dispatch.md` — Source of the wave/package/lane model, the expected-net-profit objective, the per-delay/per-missed penalty model, and the delay_hint semantics that the new route-selection rule operationalizes.
- `workspace:/docs/attachments.md` — Defines /uploads as the upload root cited in the Inputs section for the request-named wave and TSV files.
