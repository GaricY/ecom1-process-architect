# bp_background_decoys v0004

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-22T00:02:07+00:00`
- parent: `v0003`

## Rationale

The four old decoy docs and /docs/README.md were removed; nine new background/culture docs appeared (company-history, founders-and-ownership, origin-facts-and-firsts, store-expansion-history, brand-identity, mission-vision-values, jobs-to-be-done, operating-culture, target-audience), each ending with an explicit no-authorization Boundary. Re-derived the decoy catalog and its refs-exclusion list against the new docs. /docs/employees.md is operational, not a decoy, and is excluded.

## Rollback

Restore bp_background_decoys v0003 content listing the four removed decoy docs and /docs/README.md.

## Dependencies
- `workspace:/docs/company-history.md` — Founding narrative, factual anchors, and the no-authorization boundary.
- `workspace:/docs/founders-and-ownership.md` — Founder/owner biographies and the no-authorization boundary.
- `workspace:/docs/origin-facts-and-firsts.md` — Firsts/dates and the not-current-record boundary.
- `workspace:/docs/store-expansion-history.md` — Branch history and the 'use current store records' boundary.
- `workspace:/docs/brand-identity.md` — Brand voice/symbols and the no-live-outcome boundary.
- `workspace:/docs/mission-vision-values.md` — Company intent and the no-override boundary.
- `workspace:/docs/jobs-to-be-done.md` — Customer jobs and the no-decision boundary.
- `workspace:/docs/operating-culture.md` — Culture phrases/rituals (e.g. 'manager approved' stories) and the memory-vs-evidence boundary.
- `workspace:/docs/target-audience.md` — Audience segments and the 'known != identity' boundary.
