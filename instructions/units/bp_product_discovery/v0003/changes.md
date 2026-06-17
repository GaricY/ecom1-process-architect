# bp_product_discovery v0003

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-05-21T01:23:38+00:00`
- parent: `v0001`

## Rationale

On a catalogue product-kind count question, the Executor found the matching reporting update under /docs/policy-updates/ that names the catalogue count workflow and the requested product kind, but dismissed it because the update's filename and 'Operating day:' header referenced a day other than /bin/date, and returned a plain COUNT(*). The README's matching rule lists workflow, product kind, operating day, city, family hold, and similar scope as alternatives joined by 'or'; a workflow + kind match is sufficient. This edit makes that explicit in step 3, adds an anti-pattern against dismissing a scope-matching update on date grounds, and spells out the (narrow) conditions under which a date-only update can be dismissed.

## Rollback

Create a new version from v0001 content if the new step-3 matching grammar or the date-dismissal anti-pattern proves too aggressive (e.g. starts applying updates that were genuinely retired).

## Dependencies
- `workspace:/docs/README.md` — Defines the catalogue reporting rule, the reporting-update folder list, and the scope-dimension matching grammar this BP now quotes and operationalises in step 3.
- `bin_help:sql.help.txt` — Table shapes for products, inventory, stores, and product_kinds — the BP names these tables in step 2 and in the count-restriction translation.
