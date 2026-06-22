# bp_returns v0008

- mode: `failure_fix`
- created_by: `human`
- created_at: `2026-05-30T10:52:15+00:00`
- parent: `v0007`

## Rationale

Run 20260530-125612 (ecom1-prod): yes/no token regression (live /AGENTS.MD = ja/nein). This BP echoed the stale literal TRUE(1)/FALSE(0) in the return-state yes/no lookup step. De-hardcoded to 'the yes/no token defined in the live /AGENTS.MD'.

## Rollback

bp_admin rollback bp_returns --from this version if the live-read phrasing regresses return-state lookups.

## Dependencies
- `workspace:/docs/returns.md` — Both gate sets, refund_manager role, the approved->refund_pending->closed sequence, the /bin/refund invocations, and the prohibition on editing return files by hand.
- `workspace:/docs/security.md` — Identity/ownership/role rule named verbatim as a prerequisite by returns.md.
- `bin_help:refund.help.txt` — Tool signatures for approve <return_id> and close <return_id> (replaces the retired /bin/payments approve-refund|refund).
- `bin_help:payments.help.txt` — Confirms /bin/payments no longer carries refund verbs (only recover-3ds).
