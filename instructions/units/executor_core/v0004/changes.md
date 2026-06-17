# executor_core v0004

- mode: `manual_update`
- created_by: `codex`
- created_at: `2026-05-21T17:56:35+00:00`
- parent: `v0002`

## Rationale

Adds a mandatory scratchpad business_process classification before final submission. The Executor records the process it judges to have governed the decision as a process filename with .md examples, while the orchestrator stores both raw and normalized names for reporting.

## Rollback

Retire this version to fall back to v0002 if the extra scratchpad bookkeeping causes submission regressions or distracts the Executor from the task format.
