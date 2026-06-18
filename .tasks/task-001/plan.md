# Plan: Evidence ledger process refactor

1. Update `executor_core` so the canonical topic-section contract uses
   `Evidence ledger`, not `Refs to set in scratchpad`.
2. Update `bp_refs` to own the shared Evidence ledger model:
   `read_set`, `decision_set`, `refs`, evidence roles, privacy/cross-boundary
   safety, live-path/no-vault/no-decoy/dedup rules, and final checklist.
3. Update `bp_submission_terminal` so it only checks terminal readiness:
   the ledger is already classified through `refs.md` plus the topic BP,
   `OUTCOME_OK` mutations have post-state reads, blocked-message privacy is
   checked, message format is final, and `submit_and_exit` is last.
4. Convert active topic BPs from `Refs to set in scratchpad` to local
   `Evidence ledger` sections:
   `identity_and_auth`, `privacy_and_disclosure`, `fraud_risk_review`,
   `product_discovery`, `basket_lifecycle`, `checkout`, `discount`,
   `payments_3ds_recovery`, `returns`, `date_and_time`, `background_decoys`,
   and `os_tooling_incidents`.
5. Add helper-level evidence output to `policy_update_scan` if needed, so
   matched update docs and rejected candidates are explicitly separated.
6. Publish changes only as new immutable `instructions/units/<id>/vNNNN/`
   versions. Do not edit existing versions in place and do not commit.
7. Run `PA_fix` against the refactored process set as a validation pass,
   archive its proposed fixes under
   `.tasks/task-001/pa_fix_run_20260618-034209/`, and use the failures to
   identify systemic refactor gaps rather than fitting to dev-world tasks.
8. Apply only systemic refactor-completion fixes from that analysis, such as
   shared request-named input evidence and required safe gate evidence that a
   topic BP failed to inherit. Keep task-specific overfit out of the active
   process versions.
9. Verify with `git diff`, absence of active `Refs to set in scratchpad`,
   instruction-store preflight, and manifest/dependency sanity checks.
