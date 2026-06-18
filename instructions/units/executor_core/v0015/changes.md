# executor_core v0015

- mode: `failure_fix`
- created_by: `human`
- created_at: `2026-06-18T08:01:43+00:00`
- parent: `v0014`

## Rationale

Completes the Evidence ledger refactor at the executor contract layer by
removing duplicated refs-model details from `executor_core`. The core prompt now
keeps only routing/readiness invariants and delegates bucket semantics, safety
rules, and citation projection to `refs.md` plus the selected topic BP.

## Rollback

Create a new version from the parent content if this delegation makes executor
terminal readiness too weak.
