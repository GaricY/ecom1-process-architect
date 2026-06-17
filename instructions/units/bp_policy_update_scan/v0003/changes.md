# bp_policy_update_scan v0003

- mode: `failure_fix`
- created_by: `codex`
- created_at: `2026-05-26T15:30:16+00:00`
- parent: `v0002`

## Rationale

Restore baseline-shaped dated-update discovery: inspect the live /docs tree, treat README folders as examples rather than a closed list, and avoid hard-coded child folder names.

## Rollback

Create a new version from v0002 if live-tree discovery becomes too broad or reads unrelated background docs.

## Dependencies
- `bin_help:date.help.txt` — Trusted date/timestamp provider used for operating-day and lockout comparisons.
