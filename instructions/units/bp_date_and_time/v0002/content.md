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
4. For reporting-update folder matching under `/docs/current-updates/`, `/docs/policy-updates/`, `/docs/ops-policy-notes/`, `/docs/catalogue-addenda/` — the "operating day" in an update's filename or its "Operating day:" header is a scope **dimension**, not a TTL. The README enumerates the scope dimensions ("catalogue count workflow, requested product kind, operating day, city, family hold, or similar scope") as alternatives, joined by "or". An update is a matching update when any one of those dimensions lines up with the request — typically the workflow plus the requested product kind, or the city / family the request implies. Apply `/bin/date` as a filter only when:
   - the request itself is scoped to a specific day ("today's count for ..."), AND
   - the update's only named scope dimension is an operating day,

   in which case the update's day must match `/bin/date`. Otherwise — when the update names the workflow plus the product kind, or names a city / family that matches — the update is authoritative regardless of how old its date label is. The sibling BP ([product_discovery](product_discovery.md), basket / payment BPs as relevant) applies the update's content rule.

## Outcomes

- This BP does not produce a final outcome on its own. It is a building block. The sibling BP that invoked it produces the outcome.

## Refs to set in scratchpad

- This BP does not by itself add refs. The sibling BP records the policy and record paths it actually applied.
- If a matching reporting update under `/docs/current-updates/` (or one of the other reporting-update folders) was applied to the answer, cite that update's path in the sibling BP's refs — including updates whose date label is older than `/bin/date` when their workflow / kind / city / family scope matched.

## Anti-patterns

- Trusting a SQL `CURRENT_DATE` / `datetime('now')` value. From `/bin/README.md` (referenced in the business-process map): the SQL date provider is broken.
- Trusting a `created_at` field as "now" — `created_at` is the record's birth time, not the current operating day.
- Trusting a date that appears in a `/docs/` operational-background story (Donaustadt 01:40, Graz Annenstrasse 2026-03-11, warehouse cutover 2026-04-12) as runtime "now". Those are narrative timestamps in [background_decoys](background_decoys.md).
- Skipping `/bin/date` on a request that *itself* names "today" / "this operating day" / a specific freshness window — those comparisons require the trusted runtime date.
- **Treating the date in a reporting update's filename or "Operating day:" header as a TTL that expires the update.** It is one scope dimension among several. If the update names the workflow and the requested product kind (or the city / family the request implies), it applies even when its date label is older than `/bin/date`. See [product_discovery](product_discovery.md) for the catalogue-count case.

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived.

- `AGENTS.MD` — session-start sequence (`/bin/date` + `/bin/id` + `tree`).
- `bin-help/date.help.txt` — the trusted date provider's interface.
- `/docs/README.md` — reporting-update folder list and scope-dimension matching grammar (it determines how `/bin/date` interacts with dated updates).
