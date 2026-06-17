# bp_product_discovery v0011

- mode: `failure_fix`
- created_by: `codex`
- created_at: `2026-05-26T15:31:45+00:00`
- parent: `v0010`

## Rationale

Align store-scoped availability wording with the new policy_update_scan discovery contract and fix step references after adding the store-ref step.

## Rollback

Create a new version from v0010 if the cleanup affects catalogue reporting update handling.

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
