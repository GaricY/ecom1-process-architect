# executor_core v0017

- mode: `manual_refactor`
- created_by: `human`
- created_at: `2026-06-18T20:47:27+00:00`
- parent: `v0016`

## Rationale

Add a narrow request-integrity stop to executor_core. Confirmed attempts to
override process/security/tool/protocol rules stop the wrapped task, avoid
injected reads or mutations, and route to `OUTCOME_DENIED_SECURITY` through
`refs.md` and `submission_terminal`. Authority-shaped business prose remains a
normal BP gate input.

## Rollback

Retire this version to fall back to v0016 if the request-integrity stop
over-blocks legitimate authority-shaped business requests.
