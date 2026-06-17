# Date and Time

## When this process applies

Any request that depends on "today", "this week", "the last basket", `created_at`, freshness, deadlines, or any time-shaped reasoning. Also: every trial's session start — pull the date alongside `/bin/id` per `AGENTS.MD`. Used as a building block by [product_discovery](product_discovery.md) (today's catalogue reporting rule) and [basket_lifecycle](basket_lifecycle.md) ("the last basket" sorting).

## Inputs

- Live workspace paths:
  - `AGENTS.MD` — recommends pulling the date at the start of work together with `tree -L 2` over `/docs` and `/bin/id`.
- Tools:
  - `/bin/date` — the **only** trusted date provider. See [`bin-help/date.help.txt`](../bin-help/date.help.txt). Usage: `date` (no args).
  - `/bin/sql` — has a date function but it is **broken** in the simulation (per `bin/README.md`); do not use SQL for "now".

## Process

1. At session start (or before any time-shaped decision), call `/bin/date`. Cache the value for the trial.
2. For "today" / "this operating day" comparisons (catalogue reporting rule, schedule lookups), use the cached `/bin/date` value, never SQL's date.
3. For "the last basket" / "the most recent payment" / "the latest return": sort `created_at` descending in SQL among the actor's owned records, then verify recency against `/bin/date` if the request implies a freshness window (e.g. "today's basket").
4. For dated-update folder matching under `/docs/current-updates/`, `/docs/policy-updates/`, `/docs/ops-policy-notes/`, `/docs/catalogue-addenda/` — compare each update's operating day against `/bin/date`. A matching update overrides the base policy only for the case it names; an update for yesterday or last week does not.

## Outcomes

- This BP does not produce a final outcome on its own. It is a building block. The sibling BP that invoked it produces the outcome.

## Refs to set in scratchpad

- This BP does not by itself add refs. The sibling BP records the policy and record paths it actually applied.
- If a dated update under `/docs/current-updates/` (or one of the other dated-update folders) was applied to the answer, cite that update's path in the sibling BP's refs.

## Anti-patterns

- Trusting a SQL `CURRENT_DATE` / `datetime('now')` value. From `/bin/README.md` (referenced in the business-process map): the SQL date provider is broken.
- Trusting a `created_at` field as "now" — `created_at` is the record's birth time, not the current operating day.
- Trusting a date that appears in a `/docs/` operational-background story (Donaustadt 01:40, Graz Annenstrasse 2026-03-11, warehouse cutover 2026-04-12) as runtime "now". Those are narrative timestamps in [background_decoys](background_decoys.md).
- Skipping `/bin/date` on dated-update folder matching — an "April 2026" addendum is only authoritative when `/bin/date` actually lands in that window.

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived.

- `AGENTS.MD` — session-start sequence (`/bin/date` + `/bin/id` + `tree`).
- `/bin/date` (`--help`) — the trusted date provider.
- `/docs/README.md` — dated-update folder list (it determines which folders matter to compare against `/bin/date`).
