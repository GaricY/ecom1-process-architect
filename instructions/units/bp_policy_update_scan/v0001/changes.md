# bp_policy_update_scan v0001

- mode: `initial_migration`
- created_by: `codex`
- created_at: `2026-05-26T08:22:43+00:00`

## Rationale

Create a shared helper for dated/topic policy updates that had been duplicated across product discovery, discount, 3DS recovery, and date/time. The helper owns bounded scanning, date-as-scope semantics, topic-folder sibling updates, and literal override scope.

## Rollback

Route dated-update logic back into the domain BPs if the shared helper over-triggers or hides domain-specific gates.

## Dependencies
- `bin_help:date.help.txt` — Defines the trusted date/timestamp provider for operating-day and lockout comparisons.
