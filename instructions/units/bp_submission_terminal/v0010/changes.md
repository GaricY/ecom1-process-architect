# bp_submission_terminal v0010

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-22T00:02:07+00:00`
- parent: `v0009`
- no_semantic_change: revalidated against the new dependency hashes without text edits

## Rationale

world_refresh: PA reviewed this BP and recorded it as unchanged; orchestrator re-stamped drifted dependency hashes (/AGENTS.MD) so the unit re-matches the refreshed world instead of falling back stale. No content change.

## Rollback

rollback to v0009 (content identical; only dependency hashes were re-stamped)

## Dependencies
- `workspace:/AGENTS.MD` — Live answer-format contract: the yes/no <YES>/<NO> token and response-shaping rules the terminal preflight reads from the live /AGENTS.MD rather than hardcoding.
- `static:static-instructions/runtime_prelude.py` — Defines submit_and_exit as the terminal helper that writes the answer via ws.answer and exits the snippet.
