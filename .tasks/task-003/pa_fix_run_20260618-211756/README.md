# PA Fixes From Run 20260618-211756

This directory stores Process Architect outputs from the PA prompt-refactor
validation run. These are archived proposals for review, not automatically
accepted design.

## Jobs

- `t40/` - PA failure-fix for archived payment fraud review; wrote
  `bp_fraud_risk_review v0008`.
- `t48/` - PA failure-fix for fraud-review over/under-capture; extended
  `bp_fraud_risk_review` to `v0009`.
- `t52/` - PA failure-fix for request-named OCR input refs; wrote
  `bp_refs v0009`.
- `t55/` - PA failure-fix for planted free-text content in a payment
  description; extended `bp_refs` to `v0010`.

Each job directory contains the PA report, decision, result, failure-fix task,
and original executor scratchpad copied from the run directory.

## Version Snapshots

- `versions/bp_fraud_risk_review_v0008/`
- `versions/bp_fraud_risk_review_v0009/`
- `versions/bp_refs_v0009/`
- `versions/bp_refs_v0010/`

Each version snapshot contains `content.md`, `diff.patch`, `changes.md`, and
`manifest.json` copied from `instructions/units`.

## Review Notes

Compared with the pre prompt-refactor PA outputs archived under
`pa_fix_run_20260618-121140` and `pa_fix_run_20260618-142842`, this run is
cleaner on ownership and conflict handling:

- `t52` improved: PA stopped patching product discovery behavior for an OCR
  task when the actual defect was a missing citation of a request-named input.
  The new `bp_refs` patch is narrow and layer-correct.
- `t40`/`t48` improved in discipline: both changes stay in the fraud topic BP,
  name the domain/evidence owner explicitly, and avoid the earlier
  cardinality-rule oscillation from `v0008` -> `v0009` -> `v0010`.
- `t55` improved mechanically but remains product-scope questionable for this
  task set: PA now recognizes the shared safety layer and rebases cleanly, but
  the proposed free-text/prompt-injection rule is still outside the intended
  task-003 refactor scope unless we choose to accept injection handling here.

Net: the PA prompt refactor improved placement and rationale quality, but it
did not fully solve scope control. The prompt now discourages wrong-owner local
patches; it still needs a stronger "defer unrelated future work" check when the
failure is a known out-of-scope class.
