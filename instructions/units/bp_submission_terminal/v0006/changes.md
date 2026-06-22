# bp_submission_terminal v0006

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-30T09:37:50+00:00`
- parent: `v0005`

## Rationale

AGENTS.MD changed the merchant reply-styling contract: yes/no answers are now exactly TRUE(1)/FALSE(0) (the <YES>/<NO> token is retired) and there is no <COUNT:N> token; AGENTS adds the SKU-lookup answer rule (single match -> bare SKU, else clarification). The Answer-format precedence section is re-derived. Reads in the terminal snippet now use /proc JSON (/bin/jq|cat) since /bin/sql is down; the unsupported-fallback rule defers to os_tooling_incidents.

## Rollback

Restore v0005 Answer format (yes/no -> <YES>/<NO>, count -> <COUNT:N>, ws.sql_rows examples).
