# bp_os_tooling_incidents v0003

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-30T09:37:50+00:00`
- parent: `v0002`

## Rationale

The grounding doc /docs/os-and-tooling-incidents-and-workarounds.md and the /bin/claude,/bin/codex 'Embrace AI' surfaces were all removed, so the documented-workaround domain no longer exists. The unit is re-grounded on the current world: AGENTS.MD's unsupported-systems rule (answer OUTCOME_NONE_UNSUPPORTED, do not place a placeholder or mutate, cite this policy) and the concrete /bin/sql outage, whose supported path is to read /proc JSON via /bin/jq|cat (per sqlite_schema.txt). Renamed in prose to 'Tooling Outages and Unsupported Systems'; still routed from bp_index.

## Rollback

Restore v0002 content (the os-and-tooling-incidents-and-workarounds.md workaround gate and the /bin/claude,/bin/codex Embrace-AI no-workaround example, claude/codex help dependencies).

## Dependencies
- `bin_help:jq.help.txt` — The JSON read tool that is the supported substitute for /bin/sql.
- `bin_help:cat.help.txt` — The raw file read tool for record reads.
