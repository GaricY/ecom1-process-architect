# bp_submission_terminal v0003

- mode: `failure_fix`
- created_by: `codex`
- created_at: `2026-05-26T19:40:43+00:00`
- parent: `v0002`

## Rationale

Add a concise terminal check that forbids blind submit: unresolved reads, lists, SQL, tool calls, or policy scans must be completed and reasoned over before the final submit snippet.

## Rollback

Create a new version from v0002 if the terminal exploration rule blocks valid programmatic final reads.

## Dependencies
- `static:static-instructions/runtime_prelude.py` — Defines submit_and_exit as the terminal helper that writes the answer via ws.answer and exits the snippet.
