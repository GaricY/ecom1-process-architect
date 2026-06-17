# bp_policy_update_scan v0002

- mode: `refresh`
- created_by: `codex`
- created_at: `2026-05-26T08:51:53+00:00`
- parent: `v0001`

## Rationale

Clarify that policy_update_scan owns shared matching mechanics and bounded candidate handling, including the root-/docs exception, so domain BPs can stop duplicating folder-scan rules.

## Rollback

Create a new version from v0001 if the root-/docs exception causes a domain BP to miss a valid update location.

## Dependencies
- `bin_help:date.help.txt` — Defines the trusted date/timestamp provider used for operating-day and lockout comparisons.
