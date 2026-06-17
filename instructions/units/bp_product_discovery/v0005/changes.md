# bp_product_discovery v0005

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-05-21T01:29:17+00:00`
- parent: `v0001`

## Rationale

Executor answered an 'how many of these N products have >= K in stock at store S' question with the correct count but dumped every candidate's products.path into refs, including a candidate that matched the property filter in SQL but had no inventory row at the store and whose /proc/catalog/<sku>.json turned out to be a stale projection row with no live file. The grader rejected the trial with 'answer contains invalid reference'. Adding a 'contributing rows only' rule to bp_product_discovery: for aggregate / count / availability answers cite only the rows that both match the criterion and have a real inventory row at the named store (plus the store and any applicable policy doc). This both shrinks refs to what the answer actually rests on and eliminates the stale-catalog-path failure mode without per-row ws.read probes, because an inventory row is a strong existence proof for the canonical file.

## Rollback

Create a new version from v0001 content (or any earlier version without the contributing-rows-only rule) if this restriction turns out to drop refs the grader actually wanted for aggregate-style discovery questions.

## Dependencies
- `workspace:/docs/README.md` — Defines the 'today's catalogue reporting rule' and the dated-update folder list this BP routes count questions through; the contributing-rows rule sits alongside that reporting check.
- `bin_help:sql.help.txt` — Documents the products / inventory / stores table shapes and the path column convention that the contributing-rows-only rule relies on (copying products.path / stores.path verbatim, and treating an inventory row as the existence proof for the catalogue file).
