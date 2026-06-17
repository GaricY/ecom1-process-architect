# bp_product_discovery v0013

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-28T18:31:45+00:00`
- parent: `v0012`

## Rationale

Schema rename in bin-help/sqlite_schema.txt + sql.help.txt. This BP queries catalogue/inventory throughout; re-derived every renamed table/column it names: products->product_variants, product_properties->product_variant_properties, families->product_families, inventory->store_inventory, available_today->available_today_quantity, sku->product_sku, kind_id->product_kind_id, family_id->product_family_id, and the canonical cite column path->record_path. Availability SQL, claim-verification SQL, refs-shaping, anti-patterns and dependencies updated. The /proc/catalog/ on-disk folder, the /AGENTS.MD reply-shaping rule, and the <YES>/<NO>/<COUNT:N> token contract are unchanged and were preserved.

## Rollback

Restore bp_product_discovery v0012 content and its old sql_table dependencies (products, product_properties, families, inventory) if the rename mapping proves wrong.

## Dependencies
- `bin_help:date.help.txt` — Trusted date provider used when product count/update handling invokes policy_update_scan.
- `bin_help:id.help.txt` — Actor identity pulled at session start (drives 'my' handling).
- `sql_table:product_variants` — Public product facts, properties JSON, and the canonical catalogue record_path.
- `sql_table:product_variant_properties` — Per-SKU property rows (product_sku, property_key, property_value_*) used for claim verification.
- `sql_table:product_families` — Family/brand/model grouping used to identify products.
- `sql_table:product_kinds` — product_kind_id and product-kind scope for count questions.
- `sql_table:store_inventory` — Store/SKU availability source: available_today_quantity keyed by (store_id, product_sku).
- `sql_table:stores` — Public store ids, record_path cite paths, city nuance targets, and open status.
