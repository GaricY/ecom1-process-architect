# bp_date_and_time v0004

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-30T09:37:50+00:00`
- parent: `v0003`

## Rationale

/bin/sql is fully down (not merely a broken now() function), so the 'SQL may contain created_at' input is re-derived to 'created_at lives in /proc JSON, read via /bin/jq|cat'; the payment three_ds.retry_after lockout comparison is added as a concrete case; decoy-timestamp anti-patterns updated to the new background docs.

## Rollback

Restore v0003 content (/bin/sql created_at input line, old decoy-doc timestamp references).

## Dependencies
- `bin_help:date.help.txt` — Trusted date/timestamp provider and output shape.
