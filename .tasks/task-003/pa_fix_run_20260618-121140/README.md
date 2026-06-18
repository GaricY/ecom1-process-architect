# PA Fixes From Run 20260618-121140

This directory stores Process Architect outputs from the post
`submission_terminal` refactor run for manual review. These are archived
proposals, not automatically accepted design.

## Jobs

- `t40/` - PA failure-fix for archived payment fraud review; wrote
  `bp_fraud_risk_review v0008`.
- `t48/` - PA failure-fix for archive fraud amount/cohort recall; extended
  `bp_fraud_risk_review` to `v0009`.
- `t52/` - PA failure-fix for OCR receipt catalogue comparison; wrote
  `bp_product_discovery v0021`.
- `t55/` - PA failure-fix for incoming payment note injection; wrote
  `bp_submission_terminal v0008`.

Each job directory contains the PA report, decision, result, failure-fix task,
and original executor scratchpad copied from the run directory.

## Version Snapshots

- `versions/bp_fraud_risk_review_v0008/`
- `versions/bp_fraud_risk_review_v0009/`
- `versions/bp_product_discovery_v0021/`
- `versions/bp_submission_terminal_v0008/`

Each version snapshot contains `content.md`, `diff.patch`, `changes.md`, and
`manifest.json` copied from `instructions/units` before removing the PA-created
versions from active instruction history.

## Review Notes

These outputs are deliberately archived instead of published as mainline
process versions.

- `bp_fraud_risk_review v0008/v0009` change fraud cohort semantics and are
  domain-learning proposals from the dev run, not `submission_terminal`
  refactor completion.
- `bp_product_discovery v0021` adds OCR-tolerant catalogue matching. That may be
  a useful future domain rule, but the observed failure was not caused by the
  terminal/refactor boundary.
- `bp_submission_terminal v0008` adds free-text injection/message-safety
  redaction. That behavior was explicitly left out of task-002 and belongs to a
  separate prompt-injection/free-text-safety task.
