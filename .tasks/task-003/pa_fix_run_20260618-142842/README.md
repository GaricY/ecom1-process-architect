# PA Fixes From Run 20260618-142842

This directory stores a later Process Architect output that was present in the
working tree while packaging task-002. It is archived here so PA-created process
versions do not remain in active instruction history.

## Jobs

- `t40/` - PA failure-fix for archived payment fraud review after applying the
  prior PA fraud proposals; wrote `bp_fraud_risk_review v0010`.

The job directory contains the PA report, decision, result, failure-fix task,
and original executor scratchpad copied from the run directory.

## Version Snapshots

- `versions/bp_fraud_risk_review_v0010/`

The version snapshot contains `content.md`, `diff.patch`, `changes.md`, and
`manifest.json` copied from `instructions/units` before removing the PA-created
version from active instruction history.

## Review Notes

`bp_fraud_risk_review v0010` is another fraud-cohort semantics proposal. It is
not part of the `submission_terminal` refactor and is not published as a
mainline process version.
