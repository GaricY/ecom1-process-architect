# bp_submission_terminal v0007

- mode: `failure_fix`
- created_by: `human`
- created_at: `2026-05-30T10:48:48+00:00`
- parent: `v0006`

## Rationale

Run 20260530-125612 (ecom1-prod): this unit owns the answer-format contract and hardcoded the yes/no token as TRUE(1)/FALSE(0), even quoting /AGENTS.MD verbatim and asserting 'older tokens are retired'. /AGENTS.MD had drifted to ja/nein, so the executor emitted the stale token on every yes/no trial. This version de-hardcodes the token: rule 3, the pre-submission check, the anti-pattern, and the Dependencies prose now say 'read the yes/no token from the live /AGENTS.MD' with no baked-in literal. /AGENTS.MD stays a content-prose dependency (world-only), not a structured dep.

## Rollback

bp_admin rollback bp_submission_terminal --from this version if the live-read token rule regresses; or re-pin a literal only once world_refresh reliably re-derives it on /AGENTS.MD drift.
