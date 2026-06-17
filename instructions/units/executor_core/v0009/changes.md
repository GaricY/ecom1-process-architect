# executor_core v0009

- mode: `hand-edit`
- created_by: `human`
- created_at: `2026-05-23T19:30:00+00:00`
- parent: `v0008`

## Rationale

Pre-render `/bin/id` and `/bin/date` at trial start; show their output
inline next to the `ws.date()` / `ws.id()` description.

In run `20260523-185835` 4 of the 7 remaining `*.stderr` files were
caused by the agent assuming `ws.id()` returns a parsed
`{"user": ..., "roles": ...}` dict and writing `identity["user"]` on
the first python step (t22 step1, t24 step1+step2, t25 step1). The
v0008 description only said "shortcut on /bin/id; the authoritative
agent identity" — no shape, no example. The agent built a reasonable
but wrong mental model.

Identity and sim-date are static for the trial, so the right move is
to materialise their output **before** the agent runs, the same way
`bin-help/` and `tree.md` are pre-rendered. The agent reads the value
inline; no tool call needed for the 95% case.

## Change

`### Runtime tools` (around line 160): the two `ws.date()` /
`ws.id()` bullets gained an inline REPL-style block with placeholders
`{{TRIAL_DATE}}` and `{{TRIAL_IDENTITY}}`. The resolver substitutes
these at render time using output captured by the bootstrap helper.

No other section touched. `## Security / privacy` still says "Identity
comes from `ws.id()` only" — the pre-rendered block IS that output, so
the trust statement remains accurate.

## Resolver contract

`_render_unit` does `str.replace` for `{{TRIAL_IDENTITY}}` and
`{{TRIAL_DATE}}` after reading `content.md`. Any residual `{{...}}`
token in the rendered output raises — fail loud on typos and on
future placeholders that nobody wired up.

## Rollback

Retire and run `bp_admin rollback executor_core --from v0008` if this
regresses. The resolver substitution is harmless on the v0008 text
(no placeholders → no substitution), so the rollback does not require
orchestrator changes.
