# bp_os_tooling_incidents v0004

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-22T00:02:07+00:00`
- parent: `v0003`

## Rationale

The workaround domain is removed: /docs/os-and-tooling-incidents-and-workarounds.md is gone and the /bin/claude and /bin/codex 'Embrace AI' surfaces no longer exist. Neutralized to record the one live degradation (/bin/sql cluster-down -> read /proc per the reconstructed-projection schema header, a documented data path, not a workaround) and to route any other unavailable tool to OUTCOME_NONE_UNSUPPORTED citing /AGENTS.MD. Removed from active routing in bp_index.

## Rollback

Restore bp_os_tooling_incidents v0003 content with the os-and-tooling-incidents doc and claude/codex 'Embrace AI' dependencies and re-add its index route.

## Dependencies
- `workspace:/AGENTS.MD` — The unsupported-system rule cited when a required tool is unavailable with no alternative.
- `bin_help:id.help.txt` — Actor classification via identity_and_auth.
