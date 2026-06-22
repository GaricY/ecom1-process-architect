# Branch Availability and Inventory

## When this process applies

Any branch inventory, availability, or stock-count question: "is SKU X available today at branch Y?", "how many of X are in stock at Y?", "which of these are available?", "is it due within N days?", plus inventory **export** requests for a product family. `/AGENTS.MD`: "For branch inventory, availability, or stock-count questions, follow `/docs/availability-checks.md`." Information-only by default; the export sub-workflow writes a report file only. For catalogue/SKU identity (not stock) questions, use [product_discovery](product_discovery.md).

## Inputs

- Live workspace paths:
  - `/proc/locations/<city>/<store_id>.json` — the branch (store) record; resolve the target branch first.
  - The branch's inventory rows — `location_inventory(store_id, sku, on_hand, reserved)` and incoming rows `location_inventory_incoming(store_id, sku, arrival_in_days, quantity)` (shapes in `bin-help/sqlite_schema.txt`).
  - `/proc/catalog/<brand>/<sku>.json` — for the export, to enumerate every SKU in a `family_id`.
  - `/docs/availability-checks.md` — the authoritative availability/inventory/export policy.
- Tools:
  - `/bin/availability <store_record_path> <sku>...` — prints same-day availability per SKU as `max(on_hand - reserved, 0)`; missing SKUs return `0`.
  - `/bin/jq` / `/bin/cat` — read store, inventory, incoming, and catalog JSON. `/bin/sql` is unavailable — see [os_tooling_incidents](os_tooling_incidents.md).
  - `/bin/date` — only if the request imposes a date/window (see [date_and_time](date_and_time.md)).
  - `ws.write` — **only** for an export report file, and never to catalogue/store/inventory records.

## Process

1. Call `/bin/id` (cheap; also drives "my" handling). Availability answers do not depend on actor identity.
2. Resolve the target branch. Read `/proc/locations/<city>/<store_id>.json`. If a city has multiple branches and the request uses branch wording, disambiguate from the store records' own fields (`name`, `city`, `address_line_1`) — there is no separate branch-nuance README. Keep rejected branches out of `refs`.
3. **Same-day availability.** From `/docs/availability-checks.md`: "Use only branch inventory rows … Same-day availability is `max(on_hand - reserved, 0)`. If a SKU is absent from a branch inventory record, treat that SKU as `0` same-day availability at that branch." Use `/bin/availability <store_record_path> <sku>...` (or read `location_inventory` directly). A missing inventory row and an observed `0` are both "not available today."
4. **Incoming stock.** From `/docs/availability-checks.md`: "Incoming stock counts only when the user asks to include incoming stock. When the user gives a due-within window, include only incoming rows with `arrival_in_days` inside that window." Read `location_inventory_incoming`; do not fold incoming into same-day unless the user asked.
5. **Stock-count / "how many available today".** Compute the same-day availability for the SKU(s) at the branch and answer the count. Treat absent rows and `0` as zero.
6. **Read-only guarantee.** From `/docs/availability-checks.md`: "Availability checks are read-only unless the user asks for an export file. Do not mutate catalogue, store, or inventory records." Never run a mutating tool for a plain availability/stock answer.

### Inventory export (only when the user asks for an export file)

From `/docs/availability-checks.md`:

> When exporting inventory for a product family, include every product whose product JSON has the requested `family_id`, even if that SKU is absent from the branch inventory.
> Sort export rows alphabetically by SKU.
> For today's date column, write same-day availability. For each future date column, write the incoming quantity arriving exactly on that date. Use `0` when there is no branch inventory row or no incoming quantity for that date.

1. Enumerate every `/proc/catalog` SKU whose product JSON `family_id` matches the request (include even SKUs absent from branch inventory).
2. Sort rows alphabetically by SKU.
3. Today's column = same-day availability (`max(on_hand - reserved, 0)`); each future date column = incoming `quantity` arriving exactly that date (match `arrival_in_days` to the column date via `/bin/date`); `0` when no row.
4. Write the export **only** as the requested report file ("Export writes are report files only"); do not touch catalogue/store/inventory records.

## Outcomes

- `OUTCOME_OK`: the availability/stock answer (or export report) is produced from branch inventory rows with the right shape.
- `OUTCOME_NONE_UNSUPPORTED`: the request needs data not present in the `/proc` projection, or a mutation the runtime does not support.
- `OUTCOME_NONE_CLARIFICATION`: the request names a city with multiple branches and the branch is not determinable from the request and store records.

## Refs to set in scratchpad

- The selected branch's `/proc/locations/<city>/<store_id>.json` — public location evidence for the inventory query. Do not include rejected branches.
- For a stock/availability answer about specific SKUs: include a product's `/proc/catalog/<brand>/<sku>.json` only when it has an observed positive same-day availability at the queried branch and passes the test. A SKU with no inventory row, or observed `0`, is not cited as availability evidence even if it counts toward a "fewer than K" / "out of stock" count — keep it in `scratchpad["decision"]`.
- For an export: cite the resolved catalogue product records the export rows identify and the queried branch record; cite the written report file path if the answer references it (an output artifact, per [refs](refs.md)).
- `/docs/availability-checks.md` when the answer applied the availability/export rules.
- See [refs](refs.md) for the construction contract.

## Anti-patterns

- Folding incoming stock into same-day availability when the user did not ask for incoming.
- Including incoming rows outside the due-within window the user gave.
- Treating a missing inventory row as "probably available" — a missing row is `0`.
- Citing a SKU with no inventory row or observed `0` in `refs` for a pure availability answer.
- Mutating catalogue/store/inventory records for an availability/stock question — these are read-only.
- Writing an export anywhere other than the requested report file, or treating an export as a commerce-record mutation.
- Using a background doc (store-expansion-history, etc.) for current open/closed or stock state — use current `/proc/locations` records. See [background_decoys](background_decoys.md).
- Trying `/bin/sql` for inventory — it is down; read `/proc/locations` inventory via `/bin/availability` / `/bin/jq`.

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived.

- `/docs/availability-checks.md` — same-day availability formula, missing-SKU rule, incoming-stock + due-within rules, read-only guarantee, and the inventory-export contract.
- `/bin/availability` (`--help`) — `availability <store_record_path|-> <sku>...`; `max(on_hand - reserved, 0)`, missing SKU → `0`.
- `/bin/jq` (`--help`), `/bin/cat` (`--help`) — JSON read tools for store/inventory/incoming/catalog rows.
- `/bin/date` (`--help`) — used only when the request imposes a date/window or future-date export columns.
- `sql_table location_inventory` — `on_hand` / `reserved` per `(store_id, sku)`.
- `sql_table location_inventory_incoming` — `arrival_in_days` / `quantity` for incoming and export future-date columns.
- `sql_table locations` — branch record and `record_path` for the queried store.
- `sql_table catalog` — `family_id` enumeration and SKU records for exports.
