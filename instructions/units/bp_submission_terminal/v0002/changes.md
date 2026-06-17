# bp_submission_terminal v0002

- mode: `failure_fix`
- created_by: `codex`
- created_at: `2026-05-26T15:30:16+00:00`
- parent: `v0001`

## Rationale

Restore universal blocked-outcome message hygiene so final messages do not reveal foreign identity-scoped data learned during investigation.

## Rollback

Create a new version from v0001 if terminal message hygiene becomes too restrictive for safe public identifiers.

## Dependencies
- `static:static-instructions/runtime_prelude.py` — Defines submit_and_exit and the clean terminal behavior this BP describes.
