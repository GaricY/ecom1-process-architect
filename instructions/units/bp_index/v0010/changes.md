# bp_index v0010

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-22T08:03:27+00:00`
- parent: `v0009`

## Rationale

Routing layer. The trial was a legitimate, supported filesystem chore (delete every file under a named /tmp scratch dir, return the deleted paths sorted). The runtime performs this directly via the workspace primitives ws.find/ws.list/ws.delete/ws.write, so the expected outcome is OUTCOME_OK. The Executor read only /AGENTS.MD, reasoned 'no /bin/<tool> for filesystem cleanup -> unsupported', matched no §1 row, and fell through to §2 rule 9, submitting OUTCOME_NONE_UNSUPPORTED. Two surgical edits: (a) broaden the os_tooling_incidents routing row so a direct filesystem/OS housekeeping request reaches that BP; (b) rewrite rule 9 so it recognises the workspace filesystem primitives as a runtime capability — a request they can perform is supported (route + carry out), and unsupported is reserved for actions neither a /bin/<tool> nor a workspace primitive can do. This widens the world_refresh that introduced rule 9 / narrowed os_tooling, rather than stacking a new compensating safeguard.

## Rollback

Create a new version from bp_index v0009 content to drop the filesystem/OS housekeeping routing trigger and revert rule 9 to the plain 'no runtime tool -> OUTCOME_NONE_UNSUPPORTED' wording.

## Dependencies
- `static:static-instructions/workspace.py` — Defines the workspace filesystem primitives (ws.find/ws.list/ws.read/ws.write/ws.delete) that rule 9 and the os_tooling routing row now assert are a supported runtime capability; if these are renamed or removed, rule 9's filesystem carve-out goes stale.
