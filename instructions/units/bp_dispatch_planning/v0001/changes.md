# bp_dispatch_planning v0001

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-22T00:02:07+00:00`

## Rationale

New domain: /docs/dispatch.md plus the AGENTS.MD route ('plan a dispatch wave and pointed to a .md file') define a wave-routing/assignment planning task whose deliverable is a single JSON assignment object optimized for expected net profit. No existing BP covers it; it is information/planning, not a commerce mutation.

## Rollback

Remove the bp_dispatch_planning unit and its render path and its bp_index route.

## Dependencies
- `workspace:/docs/dispatch.md` — Wave/package/lane model, routing constraints, the expected-net-profit objective, and the exact output JSON schema.
- `workspace:/docs/attachments.md` — /uploads as the root for the request-named wave and TSV input files.
