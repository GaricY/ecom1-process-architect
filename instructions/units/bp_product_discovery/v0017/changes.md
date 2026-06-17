# bp_product_discovery v0017

- mode: `failure_fix`
- created_by: `codex`
- created_at: `2026-05-30T07:20:50+00:00`
- parent: `v0016`

## Rationale

Tighten the t45 low-stock refs rule after v0016: an observed store_inventory row is not enough for a pure availability product ref when available_today_quantity is 0. Plain 'less than / fewer than N' count semantics may still treat NULL or 0 as below the threshold, but refs must cite only positively available products that pass the predicate (for low-stock: 0 < available_today_quantity < N). This preserves the v0016 NULL-ref fix and covers the 20260530-050756 failure where a zero-quantity Engelbert Strauss SKU was rejected as an invalid product reference. Analysis: .tasks/task-030/t45_analyze_gpt.md.

## Rollback

Revert to v0016 if the grader requires product refs for observed zero-quantity rows on pure availability counts, or if non-pure catalogue identity/match refs regress.

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
