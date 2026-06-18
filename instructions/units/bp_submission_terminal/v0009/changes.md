# bp_submission_terminal v0009

- mode: `manual_refactor`
- created_by: `human`
- created_at: `2026-06-18T21:30:27+00:00`
- parent: `v0008`

## Rationale

Add a narrow terminal message-safety check for information/reporting answers
that quote record text fields. The terminal still preserves the already-selected
outcome, but it must not reproduce credential-harvesting URLs, shell/tool
commands, or process-override text from a data field when a redaction or
description preserves the requested business facts.

## Rollback

Retire this version to fall back to v0008 if the message-safety check
over-redacts legitimate answer payloads.

## Dependencies
- `workspace:/AGENTS.MD` — Live answer-format contract: the yes/no <YES>/<NO> token and response-shaping rules the terminal preflight reads from the live /AGENTS.MD rather than hardcoding.
- `static:static-instructions/runtime_prelude.py` — Defines submit_and_exit as the terminal helper that writes the answer via ws.answer and exits the snippet.
