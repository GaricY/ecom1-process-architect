# Availability and Inventory

## When this process applies

A branch availability / inventory / stock-count question: "is X available today at Y?", "how many of SKU Z are in stock at branch B?", "which branch has it today?", or an **inventory export** for a product family. `/AGENTS.MD` routes "branch inventory, availability, or stock-count questions" here. Information/read-only, except an explicit export produces a report file. For "which product / which SKU is this?", route to [product_discovery](product_discovery.md).

## Inputs

- Live workspace paths:
  - `/proc/locations/<...>.json` — store record: `id`, `name`, `city`, `is_open`, `lat`/`lon`, and `inventory[]` (each `{sku, on_hand, reserved, incoming[]{quantity, arrival_in_days}}`).
  - `/proc/catalog/<...>.json` — product records, needed for export (every SKU in a `family_id`) and to resolve the requested product.
  - `/docs/availability-checks.md` — the authoritative availability + export policy.
- Tools: `/bin/availability <store_record_path|-> <sku>...` — prints same-day availability as `max(on_hand - reserved, 0)`; missing SKUs return `0` (`bin-help/availability.help.txt`). `/bin/id`, `/bin/date` (due-within windows). SQL is unavailable — read `/proc` JSON directly.

## Process

From `/docs/availability-checks.md`:

1. Resolve the branch from the request (`/proc/locations` `name`/`city`). If a city has multiple branches and the request does not disambiguate, `OUTCOME_NONE_CLARIFICATION`. Keep rejected branches out of refs.
2. **Use only that branch's inventory rows** when answering branch availability/inventory/stock-count. Do not infer from other branches.
3. Same-day availability is `max(on_hand - reserved, 0)`. If a SKU is absent from the branch inventory, its same-day availability is `0`. Compute via `/bin/availability` (pass the branch `/proc/locations` record path and the SKUs) or directly from the inventory rows.
4. Incoming stock counts **only when the user asks** to include incoming. When the user gives a due-within window, include only incoming rows whose `arrival_in_days` is inside that window (use `/bin/date` if the window is date-based; see [date_and_time](date_and_time.md)).
5. Availability checks are **read-only** — do not mutate catalogue, store, or inventory records — unless the user asks for an export file.
6. Reply shaping: state what **is** available; for yes/no use the `TRUE(1)`/`FALSE(0)` token; for counts return the count. [submission_terminal](submission_terminal.md) owns the final format.

### Inventory export

When exporting inventory for a product family (`/docs/availability-checks.md`):

1. Include **every** product whose catalogue record has the requested `family_id`, even if that SKU is absent from the branch inventory.
2. Sort export rows alphabetically by SKU.
3. For today's date column, write same-day availability (`max(on_hand - reserved, 0)`). For each future date column, write the incoming quantity arriving **exactly** on that date. Use `0` when there is no branch inventory row or no incoming quantity for that date.
4. Export writes are **report files only** — never write to catalogue/store/inventory records. Write the report to the permitted scratch/report path.

## Outcomes

- `OUTCOME_OK`: the availability/stock/count question is answered from branch inventory, or the export report is produced with the correct rows/columns.
- `OUTCOME_NONE_CLARIFICATION`: the request names a city with multiple branches and does not pick one.
- `OUTCOME_NONE_UNSUPPORTED`: the branch or required data is not present.

## Evidence ledger

`policy_docs_applied`:

- `/docs/availability-checks.md` when its availability or export rule shaped the answer.

`answer_records`:

- The queried `/proc/locations/<id>.json` branch record.
- For availability of specific products, the relevant `/proc/catalog/<sku>.json` records the answer identifies; for exports, the family's catalogue records.

`considered_not_cited`:

- Rejected branches from city disambiguation.
- SKUs with no inventory row or `0` availability when the answer does not positively identify them.

`refs_must_include`:

- The selected branch's `/proc/locations/<id>.json`.
- Catalogue product records the answer positively identifies (e.g. "these SKUs are available", or the exported family's products).

`refs_must_not_include`:

- Rejected branches and `bin-help` paths.

`post_state_records`:

- none; availability is read-only and exports write only report files (not commerce records).

## Anti-patterns

- Answering branch availability from another branch's rows, or from a stale read instead of the live inventory.
- Treating a SKU missing from branch inventory as available — missing = `0`.
- Counting incoming stock when the user did not ask, or ignoring the due-within `arrival_in_days` window.
- Mutating catalogue/store/inventory records; the only write allowed is an export report file.
- Omitting a family SKU from an export because it is absent from the branch inventory — include it with `0`.

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived.

- `/docs/availability-checks.md` — the same-day availability formula, incoming-stock and due-within rules, read-only constraint, and the inventory-export schema.
- `/bin/availability` (`--help`) — the same-day availability tool and its `max(on_hand - reserved, 0)` / missing-SKU-`0` contract.
- `locations` (`/proc/locations`) — branch record and `inventory` rows (`on_hand`, `reserved`, `incoming.arrival_in_days`).
- `catalog` (`/proc/catalog`) — `family_id` and SKU set used to resolve products and build family exports.
