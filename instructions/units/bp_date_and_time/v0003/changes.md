# bp_date_and_time v0003

- mode: `refresh`
- created_by: `codex`
- created_at: `2026-05-26T08:22:43+00:00`
- parent: `v0002`

## Rationale

Narrow date_and_time to trusted clock and timestamp comparison. Dated policy/update matching semantics move to bp_policy_update_scan.

## Rollback

Create a new version from v0002 if removing dated-update matching from this BP causes stale/update misclassification.

## Dependencies
- `bin_help:date.help.txt` — Trusted date/timestamp provider interface.
