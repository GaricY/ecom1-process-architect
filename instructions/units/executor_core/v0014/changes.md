# executor_core v0014

- mode: `manual_refactor`
- created_by: `human`
- created_at: `2026-06-18T00:30:07+00:00`
- parent: `v0013`

## Rationale

Tighten executor_core so the lower submission contract uses the new Evidence ledger/read_set/decision_set/final refs model instead of the old flat scratchpad refs summary.

## Rollback

Retire this version to fall back to v0013, or issue a new manual_refactor version with adjusted executor ledger wording.
