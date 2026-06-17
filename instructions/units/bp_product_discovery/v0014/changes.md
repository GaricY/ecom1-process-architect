# bp_product_discovery v0014

- mode: `failure_fix`
- created_by: `human`
- created_at: `2026-05-28T20:37:49+00:00`
- parent: `v0013`

## Rationale

Token-contract consolidation (companion). Step 6 drops the inline 'For yes/no include <YES>... for a count <COUNT:N>' clause — the lone surviving correct copy, but a duplicate that contradicted the (broken) executor_core/bp_index versions and let the agent resolve the conflict the wrong way — in favour of a pointer to submission_terminal Answer format. Keeps the product-discovery-owned availability/store reply-shaping rule and its existing /AGENTS.MD prose dependency. Dependency contract unchanged (prose-only). Analysis: .tasks/task-024/token_regression.md + token_home_consolidation.md.

## Rollback

Revert to v0013 if discovery yes/no answers miss the pointer; if so, re-add the one-line token clause to step 6.

## Dependencies
- `bin_help:date.help.txt` — Trusted date provider used when product count/update handling invokes policy_update_scan.
- `bin_help:id.help.txt` — Actor identity pulled at session start (drives 'my' handling).
- `sql_table:product_variants` — Public product facts, properties JSON, and the canonical catalogue record_path.
- `sql_table:product_variant_properties` — Per-SKU property rows (product_sku, property_key, property_value_*) used for claim verification.
- `sql_table:product_families` — Family/brand/model grouping used to identify products.
- `sql_table:product_kinds` — product_kind_id and product-kind scope for count questions.
- `sql_table:store_inventory` — Store/SKU availability source: available_today_quantity keyed by (store_id, product_sku).
- `sql_table:stores` — Public store ids, record_path cite paths, city nuance targets, and open status.
