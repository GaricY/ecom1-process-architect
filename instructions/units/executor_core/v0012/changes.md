# executor_core v0012

- mode: `failure_fix`
- created_by: `human`
- created_at: `2026-05-28T20:37:48+00:00`
- parent: `v0011`

## Rationale

Token-contract consolidation (companion to bp_submission_terminal new version). Replaces the '## Answer format' section, which since v0002 over-generalized a bare-%d count fix into 'only emit a token when the instruction shows it literally' and thereby silently dropped the /AGENTS.MD unconditional yes/no <YES>/<NO> requirement (run 20260528-225154: t51/t52/t53 all 0% on bare 'Yes'/'No'). The section now points to the single home in submission_terminal Answer format plus a one-line precedence summary, so the rule cannot drift again from a duplicated copy. Dependency contract unchanged (prose-only). Analysis: .tasks/task-024/token_regression.md + token_home_consolidation.md.

## Rollback

Revert to v0011 if the pointer proves too thin and the executor stops applying the format contract; if so, inline the precedence summary from submission_terminal here rather than restoring the broken v0011 text.
