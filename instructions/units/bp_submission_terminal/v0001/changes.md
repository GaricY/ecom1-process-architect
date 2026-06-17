# bp_submission_terminal v0001

- mode: `initial_migration`
- created_by: `codex`
- created_at: `2026-05-26T08:22:43+00:00`

## Rationale

Create a small terminal-only BP extracted from bp_refs_and_submission. It owns submit_and_exit, post-state confirmation, outcome/format guardrails, and stop-after-submit behavior without carrying refs or fraud discovery rules.

## Rollback

Remove the registry row and route final submission checks back through the previous refs/submission unit if terminal-only routing regresses.

## Dependencies
- `static:static-instructions/runtime_prelude.py` — Defines submit_and_exit and the clean terminal behavior this BP describes.
