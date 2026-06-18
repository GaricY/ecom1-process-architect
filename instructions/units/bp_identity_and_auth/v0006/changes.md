# bp_identity_and_auth v0006

- mode: `manual_refactor`
- created_by: `human`
- created_at: `2026-06-18T20:47:27+00:00`
- parent: `v0005`

## Rationale

Split legacy authority bait from confirmed request-integrity attacks.
Authority-shaped claims still null out as authorization and continue normal
identity/ownership gates; positive attempts to override process/security/tool
or protocol rules stop before the wrapped task and select
`OUTCOME_DENIED_SECURITY`.

## Rollback

Retire this version to fall back to v0005 if the split between authority bait
and confirmed request-integrity attack causes regressions.

## Dependencies
- `workspace:/docs/security.md` — Authoritative identity/ownership/cross-boundary policy this BP encodes.
- `bin_help:id.help.txt` — Defines /bin/id output shape used for actor and role branching.
- `workspace:/proc/employees/README.md` — Fixed per-store roster shape and role bundles used for employee lookup/classification.
