# bp_policy_update_scan v0005

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-22T00:02:07+00:00`
- parent: `v0004`

## Rationale

Light refresh: /docs/README.md (which defined the dated-update baseline and example folders) was removed, so the README-examples reference is stale. Re-grounded the helper on AGENTS.MD's 'pay attention to urgent updates' line and pure live /docs tree discovery; added that an update cannot grant a reserved role (e.g. discount_manager). Generic discovery/matching logic preserved.

## Rollback

Restore bp_policy_update_scan v0004 content (the /docs/README.md baseline example reference).

## Dependencies
- `bin_help:date.help.txt` — Trusted date/timestamp provider for operating-day and lockout comparisons.
