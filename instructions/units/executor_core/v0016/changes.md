# executor_core v0016

- mode: `manual_refactor`
- created_by: `human`
- created_at: `2026-06-18T09:07:10+00:00`
- parent: `v0015`

## Rationale

Remove the last concrete answer-format/token reminder from executor_core. The core prompt now only points to submission_terminal as the single source of truth for message payload shaping.

## Rollback

Retire this version to fall back to v0015 if the extra executor reminder is needed for payload-format reliability.
