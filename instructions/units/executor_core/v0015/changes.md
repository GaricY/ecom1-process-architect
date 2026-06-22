# executor_core v0015

- mode: `failure_fix`
- created_by: `human`
- created_at: `2026-05-30T10:48:48+00:00`
- parent: `v0014`

## Rationale

Run 20260530-125612 (ecom1-prod): /AGENTS.MD drifted the yes/no answer token from TRUE(1)/FALSE(0) to ja/nein, but the BP answer-format contract still hardcoded the stale literal; the executor answered every yes/no with the stale TRUE(1)/FALSE(0) across ~13 trials. This version adds a cross-cutting, benchmark-agnostic rule to the executor_core 'Answer format' section: the live /AGENTS.MD is the authority for every answer-format token; a token spelled out in any BP is a snapshot that may quote an older /AGENTS.MD and the live file wins. No token literal is named (stays world_refresh-safe).

## Rollback

bp_admin rollback executor_core --from this version if the live-token rule misfires; the rule is additive and benchmark-agnostic, so removing it just reverts to delegating the token to submission_terminal.
