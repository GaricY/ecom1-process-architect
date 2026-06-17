# bp_checkout v0002

- mode: `refresh`
- created_by: `codex`
- created_at: `2026-05-26T08:22:43+00:00`
- parent: `v0001`

## Rationale

Update cross-links from refs_and_submission to refs after the P0 split. Checkout semantics are unchanged.

## Rollback

Create a new version from v0001 if link-only refresh has unexpected effects.

## Dependencies
- `workspace:/docs/checkout.md` — Checkout gate set, source order, and vocabulary anti-patterns.
- `workspace:/docs/security.md` — Identity gate applied via identity_and_auth.
- `bin_help:checkout.help.txt` — Checkout tool signature.
