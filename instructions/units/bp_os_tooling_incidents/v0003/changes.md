# bp_os_tooling_incidents v0003

- mode: `manual_refactor`
- created_by: `human`
- created_at: `2026-06-18T00:26:47+00:00`
- parent: `v0002`

## Rationale

Refactor refs from a flat scratchpad list into typed Evidence ledger roles. refs.md owns the shared model and safety projection; topic BPs classify their domain evidence; submission_terminal checks the completed ledger before submit.

## Rollback

Retire this version to fall back to v0002, or issue a new manual_refactor version with adjusted ledger wording.

## Dependencies
- `workspace:/docs/os-and-tooling-incidents-and-workarounds.md` — Sole authority for the workaround-use policy: /bin/id prerequisite, employee-only gate, fail-fast wording, reference-the-specific-incident-file rule, and the boundary statement.
- `bin_help:id.help.txt` — Actor source for the employee-only gate, consumed via identity_and_auth.
- `bin_help:claude.help.txt` — The /bin/claude 'Embrace AI / account not authorized' surface used as the canonical no-documented-workaround example; if a real /docs onboarding/workaround policy for this tool appears, the no-workaround branch must be re-derived.
- `bin_help:codex.help.txt` — The /bin/codex equivalent surface; same re-derivation trigger as the claude surface.
