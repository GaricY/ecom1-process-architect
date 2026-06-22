# Date and Time

## When this process applies

Any request that depends on "today", "this week", `created_at`, freshness, deadlines, retry timestamps (e.g. the 3DS `three_ds.retry_after`), incoming due-within windows, or latest/most-recent ordering. Also: every trial's session start pulls the date alongside `/bin/id`.

This BP owns the trusted clock and timestamp comparison. [policy_update_scan](policy_update_scan.md) owns dated-update matching semantics.

## Inputs

- `/bin/date` — the only trusted date/timestamp provider (`ws.date()` is the preloaded shortcut).
- `/proc/...` records — carry `created_at` (and `three_ds.retry_after`, `incoming.arrival_in_days`) values as data; they are not the clock. SQL is unavailable in this world.

## Process

1. At session start, or before any time-shaped decision, call `/bin/date` or use the preloaded `ws.date()` value.
2. For "today" / "this operating day" comparisons, use `/bin/date`, never the harness date, wall clock, CLAUDE.md date, file modification time, or a narrative timestamp from a background doc.
3. For latest/most-recent records, sort by the record's `created_at` descending inside the actor/request scope. Use `/bin/date` only when the request also imposes a freshness window.
4. For lockout/retry timestamps (e.g. `three_ds.retry_after`, or a value returned by [policy_update_scan](policy_update_scan.md)), compare the parsed timestamp against `/bin/date`'s live value. Parse the actual `/bin/date` output if precision is unclear.
5. For incoming-stock due-within windows, compare `incoming.arrival_in_days` against the window the request defines, using `/bin/date` when the window is date-based.
6. For dated policy/update documents, do not decide match/staleness here — invoke [policy_update_scan](policy_update_scan.md), which treats date labels as scope dimensions unless the request/update makes the date a live filter or lockout.

## Outcomes

This BP produces no final outcome on its own. The invoking domain BP produces the outcome.

## Evidence ledger

`actor_or_protocol_evidence`:

- `/bin/date` result is decision evidence for "today", recency, operating-day, lockout, retry-timestamp, and freshness comparisons.

`policy_docs_applied`:

- none from this BP by itself.

`answer_records`:

- none by default; the invoking BP owns any records/policies whose answer depends on the date comparison.

`considered_not_cited`:

- Host/system clock, harness date, stale read timestamps, and filename/narrative dates used without `/bin/date`.

`refs_must_include`:

- none by itself; the invoking BP cites update docs or records actually applied.

`refs_must_not_include`:

- `bin-help/date.help.txt` and non-live timestamp sources.

## Anti-patterns

- Trusting a host/system clock or harness date instead of `/bin/date`.
- Treating a record's `created_at` (or a background doc's narrative timestamp) as runtime "now".
- Comparing a `retry_after` / lockout timestamp without first knowing the live `/bin/date` value.
- Declaring a policy update stale solely from a filename date — use [policy_update_scan](policy_update_scan.md).

## Dependencies

> If any of these dependencies change, this BP file may have become stale and must be re-derived.

- `/bin/date` (`--help`) — trusted date/timestamp provider and output shape.
