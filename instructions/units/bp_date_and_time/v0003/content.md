# Date and Time

## When this process applies

Any request that depends on "today", "this week", `created_at`, freshness, deadlines, retry timestamps, lockout windows, or latest/most-recent ordering. Also: every trial's session start pulls the date alongside `/bin/id` per the baseline operating instructions.

This BP owns the trusted clock and timestamp comparison. [policy_update_scan](policy_update_scan.md) owns dated-update matching semantics.

## Inputs

- `/bin/date` - the only trusted date/timestamp provider.
- `/bin/sql` - may contain `created_at` values, but SQL "now" functions are broken in the simulation.

## Process

1. At session start, or before any time-shaped decision, call `/bin/date` or use the preloaded `ws.date()` value for this trial.
2. For "today" / "this operating day" comparisons, use `/bin/date`, never the harness date, wall clock, CLAUDE.md date, file modification time, or SQL current-date functions.
3. For latest/most-recent records, sort by the record's `created_at` descending inside the actor/request scope. Use `/bin/date` only when the request also imposes a freshness window.
4. For lockout/retry timestamps returned by [policy_update_scan](policy_update_scan.md), compare the parsed update timestamp against `/bin/date`'s live value. If precision is unclear, parse the actual `/bin/date` output before deciding.
5. For dated policy/update documents, do not decide match/staleness here. Invoke [policy_update_scan](policy_update_scan.md), which treats date labels as scope dimensions unless the request/update specifically makes the date a live filter or lockout.

## Outcomes

This BP does not produce a final outcome on its own. The invoking domain BP produces the outcome.

## Refs to set in scratchpad

This BP does not add refs by itself. The invoking BP cites update docs or records it actually applied.

## Anti-patterns

- Trusting SQL `CURRENT_DATE`, `datetime('now')`, or equivalent.
- Treating `created_at` as runtime "now".
- Treating narrative timestamps in decoy docs as the live clock.
- Declaring a policy update stale solely from its filename date. Use [policy_update_scan](policy_update_scan.md).
- Comparing lockout timestamps without knowing the live `/bin/date` value.

## Dependencies

> If any of these dependencies change, this BP file may have become stale and must be re-derived.

- `/bin/date` (`--help`) - trusted date/timestamp provider and output shape.
