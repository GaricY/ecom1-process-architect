# bp_policy_update_scan v0004

- mode: `manual_refactor`
- created_by: `human`
- created_at: `2026-06-18T00:26:47+00:00`
- parent: `v0003`

## Rationale

Refactor refs from a flat scratchpad list into typed Evidence ledger roles. refs.md owns the shared model and safety projection; topic BPs classify their domain evidence; submission_terminal checks the completed ledger before submit.

## Rollback

Retire this version to fall back to v0003, or issue a new manual_refactor version with adjusted ledger wording.

## Dependencies
- `bin_help:date.help.txt` — Trusted date/timestamp provider used for operating-day and lockout comparisons.
