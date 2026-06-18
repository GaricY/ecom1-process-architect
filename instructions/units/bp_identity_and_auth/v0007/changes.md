# bp_identity_and_auth v0007

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-18T23:08:58+00:00`
- parent: `v0006`
- no_semantic_change: revalidated against the new dependency hashes without text edits

## Rationale

world_refresh: PA reviewed this BP and recorded it as unchanged; orchestrator re-stamped drifted dependency hashes (/docs/security.md) so the unit re-matches the refreshed world instead of falling back stale. No content change.

## Rollback

rollback to v0006 (content identical; only dependency hashes were re-stamped)

## Dependencies
- `workspace:/docs/security.md` — Authoritative identity/ownership/cross-boundary policy this BP encodes.
- `bin_help:id.help.txt` — Defines /bin/id output shape used for actor and role branching.
- `workspace:/proc/employees/README.md` — Fixed per-store roster shape and role bundles used for employee lookup/classification.
