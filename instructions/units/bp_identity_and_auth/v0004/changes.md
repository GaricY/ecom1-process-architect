# bp_identity_and_auth v0004

- mode: `world_refresh`
- created_by: `codex`
- created_at: `2026-05-29T11:30:59+00:00`
- parent: `v0003`

## Rationale

Inline a compact employee roster summary sourced from /proc/employees/README.md, and add a short role-without-supported-workflow unsupported rule.

## Rollback

Revert to the prior version if the roster note proves noisy or if the unsupported-workflow rule conflicts with a new domain BP.

## Dependencies
- `workspace:/docs/security.md` — Authoritative identity/ownership/cross-boundary policy this BP encodes.
- `bin_help:id.help.txt` — Defines /bin/id output shape used for actor and role branching.
- `workspace:/proc/employees/README.md` — Fixed per-store roster shape and role bundles used for employee lookup/classification.
