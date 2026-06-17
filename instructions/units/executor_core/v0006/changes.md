# executor_core v0006

- mode: `manual_update`
- created_by: `human-ws-sql-rows`
- created_at: `2026-05-23T00:00:05+00:00`
- parent: `v0005`

## Rationale

Document the new ws.sql_rows helper as the primary SELECT path. Demote ws.sql to the raw/escape-hatch role and assert that all three keys (exit_code, stdout, stderr) are now always present in its return dict (workspace.py: always_print_fields_with_no_presence=True). Drop the redundant two-example SQL section that bred the 'forgot exit_code check in copied streaming decoder' foot-gun.

## Rollback

To restore prior text run: uv run python -m orchestrator.bp_admin rollback executor_core --from v0005 --empty-deps
