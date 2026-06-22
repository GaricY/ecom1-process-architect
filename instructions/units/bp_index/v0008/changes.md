# bp_index v0008

- mode: `failure_fix`
- created_by: `human`
- created_at: `2026-05-30T10:48:49+00:00`
- parent: `v0007`

## Rationale

Run 20260530-125612 (ecom1-prod): yes/no token regression (live /AGENTS.MD = ja/nein). The index mentioned the stale literal TRUE(1)/FALSE(0) in the routing table and the outcome-token note. De-hardcoded both to 'the yes/no token from the live /AGENTS.MD' so the entry index no longer leaks the stale literal.

## Rollback

bp_admin rollback bp_index --from this version if the live-read phrasing causes confusion in routing.
