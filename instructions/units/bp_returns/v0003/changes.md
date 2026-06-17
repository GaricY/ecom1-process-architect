# bp_returns v0003

- mode: `refresh`
- created_by: `codex`
- created_at: `2026-05-26T08:22:43+00:00`
- parent: `v0002`

## Rationale

Update cross-links from refs_and_submission to refs after the P0 split. Return/refund semantics are unchanged.

## Rollback

Create a new version from v0002 if link-only refresh has unexpected effects.

## Dependencies
- `workspace:/docs/returns.md` — Return/refund gate sets, roles, statuses, and no-manual-edit rule.
- `workspace:/docs/security.md` — Identity/ownership prerequisite cited by returns policy.
- `bin_help:payments.help.txt` — Refund approval/finalization tool signatures.
