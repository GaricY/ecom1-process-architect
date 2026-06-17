# bp_submission_terminal v0005

- mode: `failure_fix`
- created_by: `codex`
- created_at: `2026-05-29T12:00:14+00:00`
- parent: `v0004`

## Rationale

Move the role-without-supported-workflow guard into the terminal pre-submit checks, where unsupported role-shaped actions are finalized as OUTCOME_NONE_UNSUPPORTED without manual edits.

## Rollback

Revert to v0004 if this terminal guard conflicts with a future dedicated action BP that intentionally adds a supported workflow.

## Dependencies
- `static:static-instructions/runtime_prelude.py` — Defines submit_and_exit as the terminal helper that writes the answer via ws.answer and exits the snippet.
