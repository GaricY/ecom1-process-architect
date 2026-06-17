# bp_product_discovery v0004

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-05-21T01:25:56+00:00`
- parent: `v0001`

## Rationale

Grader rejected the trial with 'answer contains invalid reference /proc/catalog/<sku>.json' for a SKU whose available_today was NULL at the store. The Executor cited all six candidate SKUs from the question in refs even though only two satisfied the 'at least 4 items' threshold. The /AGENTS.MD shaping rule says availability answers must reference only the available products, but the prior bp_product_discovery applied that rule to the message text alone and was silent about refs. The Refs to set in scratchpad section copied every candidate's products.path. This version adds an explicit 'qualifying set' Process step and rewrites the Refs section so that for availability / threshold / predicate questions only the products that pass the predicate enter refs; NULL inventory and below-threshold availability both fail the predicate. Adds a matching anti-pattern and a NULL-LEFT-JOIN clarification.

## Rollback

Create a new version from v0001 content if the qualifying-set rule turns out to be too narrow (e.g. graders for some availability questions accept candidate SKUs in refs).

## Dependencies
- `workspace:/AGENTS.MD` — Sources the reply-shaping rule (line 29: availability answers reference only available products, not unavailable ones); this BP now extends that rule to refs construction.
- `workspace:/docs/README.md` — Defines the today's catalogue reporting rule and the dated-update folder list referenced in Process step 3.
- `bin_help:sql.help.txt` — Documents the products / inventory / stores table shapes (including the path column and inventory keyed by (store_id, sku)) that Process steps 2 and 6 rely on.
