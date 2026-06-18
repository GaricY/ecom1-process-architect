# bp_returns v0007

- mode: `failure_fix`
- created_by: `human`
- created_at: `2026-06-18T07:51:05+00:00`
- parent: `v0006`

## Rationale

Completes the Evidence ledger refactor for returns after reviewing the PA_fix
run: linked payment is mandatory safe gate evidence for authorized refund
approval/finalization evaluations, but not for cross-boundary denials,
role-stop branches, missing returns, or unrelated replacement/manual-edit
requests. PA proposals remain archived under the task run artifact and are not
published as mainline instruction versions.

## Rollback

Create a new version from the parent content if this refactor-completion wording
over-constrains executor behavior.
