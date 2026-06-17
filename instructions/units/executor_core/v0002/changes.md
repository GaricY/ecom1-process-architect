# executor_core v0002

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-05-21T06:51:27+00:00`
- parent: `v0001`

## Rationale

The Executor computed the correct count (1) but submitted message="<COUNT:1>" when the instruction said `Answer in exactly format "%d" (no quotes)`. Grader returned partial credit (60%) with 'Answer should be "1", but at least it contains it' — a pure format miss. The old `## Answer format` section listed `<COUNT:7>` as a generic example for count tasks, which trained the Executor to wrap bare integers in a `<COUNT:N>` token regardless of what the instruction actually demanded. The rewrite makes the instruction's literal format clause authoritative: printf-style placeholders (`%d`, `%s`, `%.2f`) mean a bare value with no wrapping, and wrapping tokens (`<YES>`, `<COUNT:N>`, `[QTY:N]`) are only valid when the instruction itself shows that token shape. Adds an explicit pre-submission check and anti-patterns covering the exact failure mode.

## Rollback

Create a new version from v0001 content if the rewritten Answer format section is too restrictive (e.g. it makes the Executor drop required tokens on a future trial that does prescribe a `<COUNT:N>`-style literal).
