# bp_product_discovery v0015

- mode: `world_refresh`
- created_by: `codex`
- created_at: `2026-05-29T11:30:59+00:00`
- parent: `v0014`

## Rationale

Require live /proc/stores/README.md reads for multi-store city/branch-nickname disambiguation instead of inlining the branch map; add the proc README as the drift dependency.

## Rollback

Revert to the prior version if the live README read proves too costly or if store disambiguation regressions appear.

## Dependencies
- `bin_help:date.help.txt` — Trusted date provider used when product count/update handling invokes policy_update_scan.
- `bin_help:id.help.txt` — Actor identity pulled at session start (drives 'my' handling).
- `sql_table:product_variants` — Public product facts, properties JSON, and the canonical catalogue record_path.
- `sql_table:product_variant_properties` — Per-SKU property rows (product_sku, property_key, property_value_*) used for claim verification.
- `sql_table:product_families` — Family/brand/model grouping used to identify products.
- `sql_table:product_kinds` — product_kind_id and product-kind scope for count questions.
- `sql_table:store_inventory` — Store/SKU availability source: available_today_quantity keyed by (store_id, product_sku).
- `sql_table:stores` — Public store ids, record_path cite paths, city nuance targets, and open status.
- `workspace:/proc/stores/README.md` — Natural-language branch nuance used to choose between multiple stores in one city.
