# bp_fraud_risk_review v0009

- mode: `refresh`
- created_by: `process_architect`
- created_at: `2026-05-30T18:07:44+00:00`
- parent: `v0008`

## Rationale

World-base AGENTS.MD renamed the staff /proc family from /proc/staff to /proc/employees. The BP's Inputs block enumerated /proc/staff as one of the live JSON families read for risk scans, so the path is now stale and would point at a non-existent family if a future risk task touched the employees axis. Renamed the single occurrence in the Inputs bullet. The 3DS doc edit (max attempts 2 -> 3) is metadata only: this BP references max_attempts from the payment_three_ds record, never a hard-coded number, so no rewording is required for that drift.

## Rollback

Revert to v0008 (bp_admin rollback bp_fraud_risk_review --from v0008) to restore the /proc/staff wording.

## Dependencies
- `workspace:/docs/payments/3ds.md` — Legitimate 3DS workflow-state transitions used for payment invariant checks (paid-with-failed-3DS, exhausted attempts, impossible transitions).
- `bin_help:jq.help.txt` — JSON read tool used for /proc family scans now that /bin/sql is unavailable.
- `bin_help:cat.help.txt` — Raw record read tool for /proc risk scans.
