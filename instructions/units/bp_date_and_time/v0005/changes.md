# bp_date_and_time v0005

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-22T00:02:07+00:00`
- parent: `v0004`

## Rationale

Light refresh: SQL is fully removed, so the '/bin/sql may contain created_at / SQL now() is broken' framing is stale. Re-pointed timestamp sources at /proc record created_at (and three_ds.retry_after, incoming.arrival_in_days); the trusted-clock rule (/bin/date only) is unchanged.

## Rollback

Restore bp_date_and_time v0004 content (the /bin/sql created_at / SQL CURRENT_DATE references).

## Dependencies
- `bin_help:date.help.txt` — Trusted date/timestamp provider and output shape.
