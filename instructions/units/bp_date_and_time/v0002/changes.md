# bp_date_and_time v0002

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-05-21T01:23:38+00:00`
- parent: `v0001`

## Rationale

The v0001 step 4 and the 'April 2026 addendum' anti-pattern framed the operating day in a dated reporting update as a TTL ('only authoritative when /bin/date actually lands in that window'). That framing directly conflicts with /docs/README.md, which lists operating day alongside workflow / product kind / city / family hold as alternative scope dimensions. The Executor leaned on this rule to drop a scope-matching update and returned the plain count. This edit reframes the date as a scope dimension, narrows when /bin/date is a filter (request scoped to a specific day AND update scoped only by day), and rewrites the related anti-pattern to match the README and the sibling product_discovery BP.

## Rollback

Create a new version from v0001 content if the relaxed date-filter rule causes the executor to apply genuinely expired dated updates that should have been ignored.

## Dependencies
- `workspace:/AGENTS.MD` — Defines the session-start sequence (/bin/date + /bin/id + tree) this BP quotes in step 1.
- `bin_help:date.help.txt` — Interface for /bin/date, the only trusted runtime date provider this BP relies on.
- `workspace:/docs/README.md` — Defines the reporting-update folder list and the scope-dimension matching grammar that the revised step 4 and anti-pattern align with.
