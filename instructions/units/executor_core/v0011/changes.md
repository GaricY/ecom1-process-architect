# executor_core v0011

- mode: `failure_fix`
- created_by: `codex`
- created_at: `2026-05-26T19:40:43+00:00`
- parent: `v0010`

## Rationale

Remove the call-count target that encouraged merging late exploration with submission, and make unresolved investigation before submit a terminal-protocol violation.

## Rollback

Create a new version from v0010 if removing the call-count target materially increases MCP calls without reducing blind-submit patterns.
