# bp_index v0005

- mode: `failure_fix`
- created_by: `human`
- created_at: `2026-05-28T20:37:48+00:00`
- parent: `v0004`

## Rationale

Token-contract consolidation (companion). Removes the 'Answer-payload shapes inside message' bullets from section 3 — they carried the same broken 'only when the instruction asks for that literal token' qualifier (added in v0003) that contradicts the unconditional /AGENTS.MD yes/no rule (run 20260528-225154: t51/t52/t53 all 0% on bare 'Yes'/'No'). Leaves the outcome-code enum the index legitimately owns and adds a pointer to submission_terminal Answer format. The index routes; it does not define answer formatting. Dependency contract unchanged (prose-only). Analysis: .tasks/task-024/token_regression.md + token_home_consolidation.md.

## Rollback

Revert to v0004 if removing the payload bullets leaves a routing gap; the pointer should suffice since submission_terminal is read before every submit.
