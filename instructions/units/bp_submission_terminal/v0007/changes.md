# bp_submission_terminal v0007

- mode: `manual_refactor`
- created_by: `human`
- created_at: `2026-06-18T09:04:42+00:00`
- parent: `v0006`

## Rationale

Refactor submission_terminal into a thin final-payload preflight: domain outcome selection stays in the topic BP, refs projection stays in refs.md plus the topic BP, and this unit owns answer-format precedence, mutation post-state confirmation, blocked-message privacy, the single submit_and_exit call, and the stop rule.

## Rollback

Retire this version to fall back to v0006, or issue a new manual_refactor version if the terminal boundary becomes too thin or too broad.

## Dependencies
- `static:static-instructions/runtime_prelude.py` — Defines submit_and_exit as the terminal helper that writes the answer via ws.answer and exits the snippet.
