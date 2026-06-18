# PA Fixes From Run 20260618-034209

This directory stores Process Architect outputs from the post-refactor run for
manual review. These are archived proposals, not automatically accepted design.

## Jobs

- `t44/` - PA failure-fix for `employee return refund approval`; wrote
  `bp_returns v0007`.
- `t48/` - PA failure-fix for `archive payment fraud amount`; wrote
  `bp_fraud_risk_review v0008`.
- `t51/` - PA failure-fix for OCR/receipt catalogue comparison; wrote
  `bp_product_discovery v0019`.
- `t53/` - PA conflict/subsumed job for the second OCR/receipt comparison;
  final decision was covered by `bp_product_discovery v0019`.
- `t55/` - PA failure-fix for incoming payment note injection; wrote
  `bp_submission_terminal v0007`.

Each job directory contains the PA report, decision, result, task, and
scratchpad artifacts copied from the run directory.

## Version Snapshots

- `versions/bp_returns_v0007/`
- `versions/bp_fraud_risk_review_v0008/`
- `versions/bp_product_discovery_v0019/`
- `versions/bp_submission_terminal_v0007/`

Each version snapshot contains `content.md`, `diff.patch`, `changes.md`, and
`manifest.json` copied from `instructions/units`.

## Refactor Completion Follow-Up

Separate human-authored versions were created after reviewing these PA outputs:

- `executor_core v0015` - removes duplicated refs-model details from the core
  prompt and delegates bucket semantics/projection rules to `refs.md` plus the
  selected topic BP.
- `bp_refs v0009` - shared `request_named_inputs`, required safe gate evidence,
  and topic-BP inheritance rules are explicit in the shared Evidence ledger.
- `bp_returns v0007` - narrows PA's linked-payment rule to authorized refund
  approval/finalization branches, avoiding cross-boundary and unrelated
  replacement/manual-edit overreach.
- `bp_product_discovery v0019` - keeps the request-named input artifact rule for
  catalogue comparison/verification, generalized without dev-grader wording.

The archived PA snapshots are not mainline instruction-store history. Where a
human-authored follow-up uses the same version number, the mainline version is
the cleaned-up refactor-completion artifact; the PA proposal remains only in
this run archive.

PA `bp_submission_terminal v0007` is archived here but is not published in the
instruction store: embedded-link / prompt-injection behavior is out of scope for
this Evidence ledger refactor and belongs to a separate task.

PA `bp_fraud_risk_review v0008` is archived here but is not published in the
instruction store: it changes fraud cohort semantics and is therefore algorithm
learning from the dev run, not Evidence ledger refactor completion.
