# bp_policy_update_scan v0004

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-30T09:37:50+00:00`
- parent: `v0003`

## Rationale

/docs/README.md (which named the world-baseline dated-update folders and examples) was removed; the discovery basis is re-grounded in AGENTS.MD's 'scan all /docs for task-specific rules; pay attention to urgent updates' instruction; doc reads use /bin/jq|cat / ws.tree since /bin/sql is down; the background-doc exclusion list is updated to the new decoy set.

## Rollback

Restore v0003 content (reference /docs/README.md world-baseline update folders and the old decoy exclusion examples).

## Dependencies
- `bin_help:date.help.txt` — Trusted date/timestamp provider used for operating-day and lockout comparisons.
