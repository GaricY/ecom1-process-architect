# bp_background_decoys v0003

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-30T09:37:50+00:00`
- parent: `v0002`

## Rationale

All four prior decoy docs were removed (merchant-continuity, store-associate-exception-handbook, warehouse-systems-migration-runbook, powertools-agentic-os-origin-story). A new operational-background set was added and confirmed as decoys by their own Boundary statements: company-history, founders-and-ownership, origin-facts-and-firsts, store-expansion-history, brand-identity, mission-vision-values, jobs-to-be-done, target-audience, operating-culture. /docs/README.md (which defined the active-vs-background split) was removed, so the split is re-grounded in AGENTS.MD's active-policy routing list plus each doc's Boundary statement.

## Rollback

Restore v0002 content (the four old decoy docs and the /docs/README.md document-families split).

## Dependencies
- `workspace:/docs/company-history.md` — Narrative hub linking the background set; Boundary statement disclaims live authority.
- `workspace:/docs/founders-and-ownership.md` — Founder/ownership lure; explicitly does not authorize commerce actions or prove identity.
- `workspace:/docs/origin-facts-and-firsts.md` — Origin 'firsts' and dates that must not be treated as the live clock or current state.
- `workspace:/docs/store-expansion-history.md` — Branch history; defers current open/stock state to /proc/locations and /docs/availability-checks.md.
- `workspace:/docs/brand-identity.md` — Brand voice/colors lure; Boundary disclaims decision authority.
- `workspace:/docs/mission-vision-values.md` — Mission/values slogans; Boundary disclaims override of live rules.
- `workspace:/docs/jobs-to-be-done.md` — Customer-job framing; Boundary disclaims decision authority.
- `workspace:/docs/target-audience.md` — Audience segments; 'branch regular' recognition is explicitly not account identity.
- `workspace:/docs/operating-culture.md` — Culture phrases/rituals; explicitly not policy text.
