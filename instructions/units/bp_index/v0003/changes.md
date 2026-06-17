# bp_index v0003

- mode: `refresh`
- created_by: `codex`
- created_at: `2026-05-26T08:22:43+00:00`
- parent: `v0002`

## Rationale

Rewrite routing for the P0 decomposition: bp_refs_and_submission is removed from active routing and replaced with focused refs, submission_terminal, fraud_risk_review, policy_update_scan, and privacy_and_disclosure routes.

## Rollback

Create a new version from v0002 if the decomposed routing causes the executor to miss required process files.
