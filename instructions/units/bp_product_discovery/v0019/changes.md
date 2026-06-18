# bp_product_discovery v0019

- mode: `failure_fix`
- created_by: `human`
- created_at: `2026-06-18T07:51:05+00:00`
- parent: `v0018`

## Rationale

Completes the Evidence ledger refactor for product discovery after reviewing the
PA_fix run: request-named live input artifacts used as catalogue
comparison/verification baselines are mandatory evidence, while pasted task text
remains scratchpad-only. PA proposals remain archived under the task run artifact
and are not published as mainline instruction versions.

## Rollback

Create a new version from the parent content if this refactor-completion wording
over-constrains executor behavior.
