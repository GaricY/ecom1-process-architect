# bp_product_discovery v0012

- mode: `failure_fix`
- created_by: `codex`
- created_at: `2026-05-26T22:06:11+00:00`
- parent: `v0011`

## Rationale

Separate pure availability refs from non-pure availability identity/match claims so identified public products remain cited even when their stock predicate fails, while unavailable products merely considered in pure availability answers stay out of refs.

## Rollback

Create a new version from v0011 if pure availability tasks start citing unavailable products that are not identified in the final answer.

## Dependencies
- `bin_help:sql.help.txt` — Defines catalogue/inventory table shapes and SQL interface used by this BP.
- `bin_help:date.help.txt` — Trusted date provider used when product count/update handling invokes policy_update_scan.
- `bin_help:id.help.txt` — Actor identity pulled at session start.
- `sql_table:products` — Public product facts, properties, and canonical catalogue paths.
- `sql_table:product_properties` — Property rows used for claim verification.
- `sql_table:families` — Family/brand/model grouping used to identify products.
- `sql_table:product_kinds` — Kind ids and product-kind scope for count questions.
- `sql_table:inventory` — Store/SKU availability source.
- `sql_table:stores` — Public store ids, paths, city nuance targets, and open status.
