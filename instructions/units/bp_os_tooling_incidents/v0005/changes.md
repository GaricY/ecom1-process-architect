# bp_os_tooling_incidents v0005

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-22T08:03:27+00:00`
- parent: `v0004`

## Rationale

Domain owner of OS/tooling operations. v0004 (a world_refresh) narrowed this BP to only the /bin/sql degraded-tool case, so an Executor routed here for a filesystem chore would still be told 'no workaround -> unsupported'. Added a 'Supported filesystem / OS housekeeping' branch: a request to clean up/delete/move/list/write files under the path it names is carried out with ws.find/ws.list/ws.delete/ws.write, re-read to confirm post-state, then OUTCOME_OK — no /bin/<tool> and no commerce role is required for housekeeping on a named scratch path. OUTCOME_NONE_UNSUPPORTED is reserved for capabilities neither a /bin/<tool> nor a workspace primitive can perform; OUTCOME_DENIED_SECURITY still fires if a request disguises a forbidden mutation (policy/security/commerce/proc) as cleanup. The degraded-tool branch is unchanged, so the previously-removed workaround-doc/Embrace-AI concept is NOT re-introduced.

## Rollback

Create a new version from bp_os_tooling_incidents v0004 content to drop the 'Supported filesystem / OS housekeeping' branch and the workspace.py dependency, leaving only the degraded-tool handling.

## Dependencies
- `workspace:/AGENTS.MD` — The unsupported-system rule cited only when a capability is genuinely unavailable (neither a /bin/<tool> nor a workspace primitive can perform it).
- `bin_help:id.help.txt` — Actor classification via identity_and_auth for the identity/request-integrity gate that still applies to filesystem housekeeping.
- `static:static-instructions/workspace.py` — Defines the workspace filesystem primitives (ws.find/ws.list/ws.stat/ws.read/ws.write/ws.delete) that make direct filesystem/OS housekeeping a supported operation; if these are renamed or removed, the supported branch must be re-derived.
