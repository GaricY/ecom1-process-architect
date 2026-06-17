# bp_product_discovery v0002

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-05-21T01:22:36+00:00`
- parent: `v0001`

## Rationale

On a catalogue count question, the Executor located the dated update under /docs/current-updates/ that named the requested product kind and kind_id verbatim, but then declared it stale by comparing the update's Operating day against the harness/system date (CLAUDE.md's currentDate) rather than calling /bin/date. The dated update was dropped from refs, the grader required it, and the trial failed 0%. The fix expands step 3 into explicit sub-steps that (a) require /bin/date before judging any dated update stale, (b) call out that an update naming the requested kind_id verbatim is strong evidence it is today's rule and must not be dismissed without a real /bin/date call, and (c) keep /docs/README.md plus any matching dated update in refs when the reporting rule was applied. Adds matching anti-patterns and pulls /bin/date into the declared dependency set so this BP re-derives if the trusted date provider's contract changes.

## Rollback

Create a new version from v0007 (or whichever is the current parent at rollback time) content if the stricter /bin/date requirement causes Executors to over-cite dated updates that genuinely do not apply.

## Dependencies
- `workspace:/docs/README.md` — Source of the catalogue reporting rule and the list of dated-update folders the step-3 flow enumerates.
- `bin_help:sql.help.txt` — Defines the products / product_kinds / inventory / stores table shapes the count and availability queries rely on.
- `bin_help:date.help.txt` — The new step-3 flow makes /bin/date the only trusted source for the operating-day comparison on dated updates; this BP is wrong if /bin/date's contract changes.
- `bin_help:id.help.txt` — Step 1 still calls /bin/id at session start; the BP's actor handling depends on its output shape.
