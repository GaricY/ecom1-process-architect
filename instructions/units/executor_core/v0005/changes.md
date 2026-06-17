# executor_core v0005

- mode: `manual_update`
- created_by: `human-task-011`
- created_at: `2026-05-21T21:48:17+00:00`
- parent: `v0004`

## Rationale

Apply task-011 findings: drop stale snapshot ladder rung, add pre-flight checklist, document ws.sql shape with worked example, introduce local-snapshot inventory section, narrow Write(./tmp/**) permission.

## Rollback

To restore prior text run: uv run python -m orchestrator.bp_admin rollback executor_core --from v0004 --empty-deps
