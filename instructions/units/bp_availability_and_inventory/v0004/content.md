# Availability and Inventory

## When this process applies

A branch availability / inventory / stock-count question: "is X available today at Y?", "how many of SKU Z are in stock at branch B?", "which branch has it today?", a **"can I buy this exact basket today at branch B?"** question over a handed-in basket / receipt / OCR document (each enumerated line is a same-day stock check against that one branch), or an **inventory export** for a product family. `/AGENTS.MD` routes "branch inventory, availability, or stock-count questions" here. Information/read-only, except an explicit export produces a report file. For "which product / which SKU is this?", route to [product_discovery](product_discovery.md).

## Inputs

- Live workspace paths:
  - `/proc/locations/<...>.json` — store record: `id`, `name`, `city`, `is_open`, `lat`/`lon`, and `inventory[]` (each `{sku, on_hand, reserved, incoming[]{quantity, arrival_in_days}}`).
  - `/proc/catalog/<...>.json` — product records, needed for export (every SKU in a `family_id`), to resolve the requested product, and to cite each SKU the request names.
  - `/docs/availability-checks.md` — the authoritative availability + export policy.
- Tools: `/bin/availability <store_record_path|-> <sku>...` — prints same-day availability as `max(on_hand - reserved, 0)`; missing SKUs return `0` (`bin-help/availability.help.txt`). `/bin/id`, `/bin/date` (due-within windows). SQL is unavailable — read `/proc` JSON directly.

## Process

From `/docs/availability-checks.md`:

1. Resolve the branch from the request (`/proc/locations` `name`/`city`). If a city has multiple branches and the request does not disambiguate, `OUTCOME_NONE_CLARIFICATION`. Keep rejected branches out of refs.
2. **Use only that branch's inventory rows** when answering branch availability/inventory/stock-count. Do not infer from other branches.
3. Same-day availability is `max(on_hand - reserved, 0)`. If a SKU is absent from the branch inventory, its same-day availability is `0`. Compute via `/bin/availability` (pass the branch `/proc/locations` record path and the SKUs) or directly from the inventory rows.
4. **Resolve every request-named SKU to its catalogue record.** `/bin/availability` accepts bare SKU strings and never surfaces a catalogue path, so when the request enumerates specific SKUs (or names a single SKU), also resolve each named SKU to its live `/proc/catalog/<brand>/<sku>.json` record (e.g. `ws.find` on `/proc/catalog` by `sku`) so it can be cited. A SKU whose same-day availability is `0` still has a catalogue record to resolve and cite. The named cohort includes **every line of a handed-in basket / receipt / OCR document** the request points to. A handed-in SKU literal can be OCR-garbled or mistyped: if it matches no catalogue record, do **not** declare the line absent — resolve it to its real record by `brand` + product `name` (`ws.find`/`ws.list` on `/proc/catalog`, then confirm the `name`/`brand` match), and compute availability against the **resolved** SKU. That resolved catalogue record — not the raw literal — is the line's cohort member.
5. Incoming stock counts **only when the user asks** to include incoming. When the user gives a due-within window, include only incoming rows whose `arrival_in_days` is inside that window (use `/bin/date` if the window is date-based; see [date_and_time](date_and_time.md)).
6. Availability checks are **read-only** — do not mutate catalogue, store, or inventory records — unless the user asks for an export file.
7. Reply shaping: state what **is** available; record the boolean verdict for a yes/no question and the integer for a count — do not hard-code an answer token here. [submission_terminal](submission_terminal.md) owns the final format and emits the live yes/no/count token from `/AGENTS.MD`.

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
- When the request names specific SKUs (a "how many of these SKUs…", "is X available…", "can I buy this basket…", or per-SKU stock question), **every named SKU is a member of the answer cohort** the count/verdict is computed over — its `/proc/catalog/<brand>/<sku>.json` record is answer evidence whether its same-day availability is at or above the threshold or `0`. A line whose handed-in SKU literal was OCR-garbled/mistyped is resolved to its real catalogue record by `brand` + `name`; that resolved record — not the raw literal — is the cohort member. For exports, the family's catalogue records.

`considered_not_cited`:

- Rejected branches from city disambiguation.
- SKUs that were **not named in the request** and only surfaced during discovery (e.g. other family members scanned but irrelevant). A SKU the request enumerated is never moved here merely because its same-day availability is `0`, nor because its handed-in SKU literal was OCR-garbled and resolved to a catalogue record under a corrected SKU — it remains a cohort member of the count/verdict and its resolved record is cited.

`refs_must_include`:

- The selected branch's `/proc/locations/<id>.json`.
- The `/proc/catalog/<brand>/<sku>.json` record of **every SKU the request names**, including SKUs whose same-day availability is `0` and lines resolved from an OCR-garbled/mistyped handed-in SKU literal (cite the **resolved** record, not the raw literal), because each is a tested member of the count/verdict. For an export, every product record in the requested family.

`refs_must_not_include`:

- Rejected branches and `bin-help` paths.

`post_state_records`:

- none; availability is read-only and exports write only report files (not commerce records).

## Anti-patterns

- Answering branch availability from another branch's rows, or from a stale read instead of the live inventory.
- Treating a SKU missing from branch inventory as available — missing = `0`.
- Dropping a request-named SKU's catalogue record from refs because its same-day availability is `0`; every SKU the request enumerated is part of the count/verdict cohort and must be cited.
- Declaring a handed-in basket/receipt line absent — or dropping its catalogue record from refs — because the OCR-garbled/mistyped SKU literal did not match a catalogue `sku`. Resolve the line to its real record by `brand` + `name`, compute availability against the resolved SKU, and cite that resolved record exactly like a line whose SKU matched verbatim.
- Citing only the branch record and policy doc while skipping the catalogue records of the SKUs the request named — `/bin/availability` taking bare SKU strings is not a licence to leave them unresolved and uncited.
- Counting incoming stock when the user did not ask, or ignoring the due-within `arrival_in_days` window.
- Mutating catalogue/store/inventory records; the only write allowed is an export report file.
- Omitting a family SKU from an export because it is absent from the branch inventory — include it with `0`.
- Hard-coding a yes/no answer literal in the reply instead of recording the boolean and letting [submission_terminal](submission_terminal.md) emit the live `/AGENTS.MD` token.

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived.

- `/docs/availability-checks.md` — the same-day availability formula, incoming-stock and due-within rules, read-only constraint, and the inventory-export schema.
- `/bin/availability` (`--help`) — the same-day availability tool and its `max(on_hand - reserved, 0)` / missing-SKU-`0` contract.
- `locations` (`/proc/locations`) — branch record and `inventory` rows (`on_hand`, `reserved`, `incoming.arrival_in_days`).
- `catalog` (`/proc/catalog`) — `family_id` and SKU set used to resolve products (including handed-in lines matched by `brand` + `name`), cite request-named SKUs, and build family exports.
