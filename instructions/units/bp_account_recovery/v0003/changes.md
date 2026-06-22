# bp_account_recovery v0003

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-22T00:02:07+00:00`
- parent: `v0002`

## Rationale

The domain is removed: /bin/account-recovery and the /run/actions control surface are gone, and security.md no longer defines account-recovery / email-change. Neutralized so that verification-link / email-change / password-reset / account-recovery requests resolve to OUTCOME_NONE_UNSUPPORTED citing /AGENTS.MD (identity_and_auth still handles any override attack). Removed from the active mutating route in bp_index.

## Rollback

Restore bp_account_recovery v0002 content with /bin/account-recovery, /run/actions/README, and the security.md account-recovery rule, and re-add its mutating index route.

## Dependencies
- `workspace:/AGENTS.MD` — The unsupported-system rule cited on the unsupported branch.
- `workspace:/docs/security.md` — Identity rule applied via identity_and_auth for cross-identity/override attempts.
- `bin_help:id.help.txt` — Actor classification.
