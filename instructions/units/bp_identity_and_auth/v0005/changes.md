# bp_identity_and_auth v0005

- mode: `manual_refactor`
- created_by: `human`
- created_at: `2026-06-18T00:26:47+00:00`
- parent: `v0004`

## Rationale

Refactor refs from a flat scratchpad list into typed Evidence ledger roles. refs.md owns the shared model and safety projection; topic BPs classify their domain evidence; submission_terminal checks the completed ledger before submit.

## Rollback

Retire this version to fall back to v0004, or issue a new manual_refactor version with adjusted ledger wording.

## Dependencies
- `workspace:/docs/security.md` — Authoritative identity/ownership/cross-boundary policy this BP encodes.
- `bin_help:id.help.txt` — Defines /bin/id output shape used for actor and role branching.
- `workspace:/proc/employees/README.md` — Fixed per-store roster shape and role bundles used for employee lookup/classification.
