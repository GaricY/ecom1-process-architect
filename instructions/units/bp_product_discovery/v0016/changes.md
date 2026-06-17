# bp_product_discovery v0016

- mode: `failure_fix`
- created_by: `human`
- created_at: `2026-05-29T14:31:11+00:00`
- parent: `v0015`

## Rationale

Restore the direction-independent v0005 invariant (a citeable availability ref must be backed by an observed store_inventory row at the queried store) that v0006 collapsed into a lower-bound-only 'passes the availability test' rule. On 'less than / at most / fewer than N' availability questions the v0006..v0015 wording made the executor cite product_variants.record_path for SKUs with no store_inventory row (NULL from the LEFT JOIN), which the grader rejects with 'answer contains invalid reference /proc/catalog/<sku>.json' (t45 = 0% in 20260529-150148 and 20260529-151240; passes only on >=K phrasings). Citeability is now gated on an observed store_inventory row regardless of predicate direction; numeric count semantics unchanged. Analysis: .tasks/task-026/analyze_failes.md.

## Rollback

Revert to v0015 if gating refs on an observed store_inventory row drops a product ref the grader required on a non->=K availability question, or if non-pure / claim-verification refs regress.

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
