# bp_submission_terminal v0008

- mode: `manual_refactor`
- created_by: `human`
- created_at: `2026-06-18T20:47:27+00:00`
- parent: `v0007`

## Rationale

Add terminal precedence for confirmed request-integrity attacks. Once selected,
the terminal keeps `OUTCOME_DENIED_SECURITY`, does not answer the wrapped
request, and relies on `refs.md` for the request-integrity citation branch.

## Rollback

Retire this version to fall back to v0007 if the terminal precedence check
blocks legitimate already-decided payloads.

## Dependencies
- `workspace:/AGENTS.MD` — Live answer-format contract: the yes/no <YES>/<NO> token and response-shaping rules the terminal preflight reads from the live /AGENTS.MD rather than hardcoding.
- `static:static-instructions/runtime_prelude.py` — Defines submit_and_exit as the terminal helper that writes the answer via ws.answer and exits the snippet.
