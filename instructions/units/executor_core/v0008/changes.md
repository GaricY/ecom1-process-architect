# executor_core v0008

- mode: `hand-edit` (bootstrapped via `bp_admin rollback --from v0007`, then content.md edited)
- created_by: `bp_admin` + human
- created_at: `2026-05-23T15:30:49+00:00`
- parent: `v0007`

## Rationale

Close the silent-KeyError class on `ws.read/list/tree/find/search/stat` responses (problem-7 in `.tasks/task-014/problem.md`).

Run `20260522-060327` had 22 invalid-key accesses across 6/50 trials.
The dangerous half (13/22) used `.get("stdout", "")` / `.get("lines", [])`
and got an empty default with no exception — the agent then proceeded
on nothing. Affected trials still scored 1.0 but burned 1–5 extra turns
each chasing the right key. Same pattern persists in post-Tier-1 runs
(`20260523-031740/0001-t38/.../execute_0015.py:11`: `readme.get("lines", [])`).

Root cause: v0007 `ws` surface listed only signatures without return
shapes. Agent had no in-prompt source for the keys and was guessing —
`.stdout` from subprocess analogy, `.lines` from `splitlines()`,
`.text` from requests-style libs.

## Change

Section `### \`ws\` surface` (around line 127): docked the
proto-derived return shape onto each `ws.*` signature, plus one bolded
reminder that file body is `content` (not `lines`/`stdout`/`text`) and
that JSON files need `json.loads(res["content"])`. One closing line
about `truncated=True` to cover the read-side counterpart of the SQL
truncation footer.

~7 lines added; no other section touched.

## Rollback

Retire and recreate via `bp_admin rollback executor_core --from v0007` if this regresses.
