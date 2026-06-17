# bp_identity_and_auth v0003

- mode: `refresh`
- created_by: `codex`
- created_at: `2026-05-26T08:22:43+00:00`
- parent: `v0002`

## Rationale

Update identity/auth cross-links for the refs/submission split and add a handoff to privacy_and_disclosure for contact-data release. The BP remains responsible for identity, ownership, and capability gates.

## Rollback

Create a new version from v0002 if the privacy handoff makes identity routing under-specific.

## Dependencies
- `workspace:/docs/security.md` — Authoritative identity/ownership/cross-boundary policy this BP encodes.
- `bin_help:id.help.txt` — Defines /bin/id output shape used for actor and role branching.
