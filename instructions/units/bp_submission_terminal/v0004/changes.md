# bp_submission_terminal v0004

- mode: `failure_fix`
- created_by: `human`
- created_at: `2026-05-28T20:37:48+00:00`
- parent: `v0003`

## Rationale

Consolidate the message answer-format / token contract into this terminal unit as its single home. Run 20260528-225154 failed t51/t52/t53 (all 0%): the agent emitted bare 'Yes'/'No' instead of <YES>/<NO>. Root cause is a regression — executor_core v0002 (a valid bare-%d count fix) over-generalized into 'only emit a wrapping token when the instruction shows it literally', and bp_index 3 v0003 inherited the same qualifier; both contradict the unconditional /AGENTS.MD rule that yes/no answers carry <YES>/<NO>. This version replaces the narrow step-6 %d anti-token rule with a full precedence contract (printf-clause -> bare; else yes/no -> <YES>/<NO> unconditional; else count -> <COUNT:N>; else prose) and an Answer format section, and adds /AGENTS.MD to the prose Dependencies block as the world-only provenance of the contract so it re-derives on reply-styling drift via world_refresh. executor_core, bp_index, and bp_product_discovery are reduced to pointers here in companion versions. Dependency contract unchanged (prose-only). Analysis: .tasks/task-024/token_regression.md + token_home_consolidation.md.

## Rollback

Revert to v0003 if the unconditional yes/no token over-fires on a task that legitimately wants a bare value with no printf clause (none observed). Narrow rollback: keep the precedence but add a guard that an explicit 'plain text / no token' instruction clause beats rule 3.

## Dependencies
- `static:static-instructions/runtime_prelude.py` — Defines submit_and_exit as the terminal helper that writes the answer via ws.answer and exits the snippet.
