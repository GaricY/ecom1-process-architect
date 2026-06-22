# bp_product_discovery v0018

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-30T09:37:50+00:00`
- parent: `v0017`

## Rationale

Branch availability/inventory/stock-count/export split out to the new bp_availability (dedicated /docs/availability-checks.md + /bin/availability); /bin/sql is down so catalogue/store reads use /proc/catalog and /proc/locations via /bin/jq|cat; /docs/README.md removed -> catalogue resolution grounded in /docs/catalogue-lookup.md and the AGENTS SKU-lookup rule; /proc/stores/README.md removed -> branch disambiguation uses store record fields; product tables folded into catalog/catalog_properties (no product_families/product_kinds tables); claim-verification yes/no tokens updated to TRUE(1)/FALSE(0).

## Rollback

Restore v0017 content (SQL projection over product_variants/store_inventory, /docs/README.md reporting rule, /proc/stores/README.md branch nuance, <YES>/<NO> claim-verification tokens, inline availability/refs logic).

## Dependencies
- `workspace:/docs/catalogue-lookup.md` — Catalogue resolution rule (resolve to exactly one product, else clarify and cite candidate SKUs); replaces the removed /docs/README.md catalogue reporting rule.
- `bin_help:jq.help.txt` — JSON read tool for catalogue/store data now that /bin/sql is unavailable.
- `bin_help:cat.help.txt` — Raw record read tool for catalogue/store JSON.
- `bin_help:date.help.txt` — Operating-day source for any dated catalogue reporting rule.
- `bin_help:id.help.txt` — Actor identity pulled at session start.
- `sql_table:catalog` — Product facts, properties, hierarchy ids, and canonical catalogue path.
- `sql_table:catalog_properties` — Per-key property rows used for claim verification.
- `sql_table:locations` — Public store ids, record path, city fields, and is_open.
