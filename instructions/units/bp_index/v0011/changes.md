# bp_index v0011

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-22T10:43:08+00:00`
- parent: `v0010`

## Rationale

Owning layer: terminal_protocol leak into the routing index. The trial failed because the Executor emitted the literal `TRUE(1)` for a yes/no question while live `/AGENTS.MD` requires `ja`/`nein` (grader: answer should be `ja`). The answer-token owner bp_submission_terminal already reads the token live from `/AGENTS.MD` and its anti-patterns forbid topic/index files from restating it, but bp_index §3 still hard-codes a `(... including the TRUE(1)/FALSE(0) yes/no token)` parenthetical — a v0009 world_refresh regression that replaced v0008's explicit 'this index does not restate it'. The conflicting v0010 fixed an unrelated filesystem-routing failure (§1 os_tooling row + §2 rule 9) and left this stale §3 literal untouched, so my concern is not subsumed; I extend v0010 rather than stack a patch. I keep all of v0010's filesystem-routing changes verbatim and only restore §3 so the index no longer restates any literal token, warning that the yes/no token is locale-specific and read live from `/AGENTS.MD`. This generalises to every yes/no task class regardless of the live locale token.

## Rollback

Create a new version from bp_index v0010 content (re-adds the `TRUE(1)`/`FALSE(0)` parenthetical in §3) if removing the hard-coded yes/no token causes Executors to omit a yes/no answer entirely.

## Dependencies
- `static:static-instructions/workspace.py` — Defines the workspace filesystem primitives (ws.find/ws.list/ws.read/ws.write/ws.delete) that the §1 os_tooling routing row and §2 rule 9 — inherited unchanged from v0010 — assert are a supported runtime capability; if these are renamed or removed, that routing carve-out goes stale.
