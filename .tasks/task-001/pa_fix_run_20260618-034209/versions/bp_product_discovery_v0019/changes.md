# bp_product_discovery v0019

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-18T01:02:53+00:00`
- parent: `v0018`

## Rationale

The trial scored 0% with the verdict 'answer missing required reference <input path>': the Executor compared an old uploaded receipt against today's catalogue prices, computed the right answer, but cited only the four /proc/catalog/<sku>.json records it compared against and dropped the /uploads/ receipt that supplied the 'old' baseline. The Executor anchored on product_discovery as its primary BP. refs.md does carry a general request_named_inputs rule, but product_discovery's typed Evidence ledger (added in the v0018 refactor) enumerates refs_must_include for stores/products/docs only and has no placement for a handed-in input artifact. That incomplete-but-authoritative topic ledger overrode the general rule. This edit adds to product_discovery a 'Comparison against a handed-in input document' task shape, a request_named_inputs ledger bucket, a refs_must_include line, an Inputs entry, and a matching anti-pattern, all requiring the request-named input artifact's absolute live path in refs when the answer's baseline/old/claimed facts came from it. Generalises to any receipt/OCR/invoice/report/attachment comparison, not this trial's specific upload.

## Rollback

Create a new version from v0018 content if requiring the request-named input artifact's path in refs causes over-citation on catalogue answers that did not actually derive a baseline fact from a handed-in document.

## Dependencies
- `bin_help:date.help.txt` — Trusted date provider used when product count/update handling invokes policy_update_scan.
- `bin_help:id.help.txt` — Actor identity pulled at session start (drives 'my' handling).
- `sql_table:product_variants` — Public product facts, properties JSON, and the canonical catalogue record_path cited for each item in a catalogue comparison or claim-verification answer.
- `sql_table:product_variant_properties` — Per-SKU property rows (product_sku, property_key, property_value_*) used for claim verification.
- `sql_table:product_families` — Family/brand/model grouping used to identify products.
- `sql_table:product_kinds` — product_kind_id and product-kind scope for count questions.
- `sql_table:store_inventory` — Store/SKU availability source: available_today_quantity keyed by (store_id, product_sku).
- `sql_table:stores` — Public store ids, record_path cite paths, city nuance targets, and open status.
- `workspace:/proc/stores/README.md` — Natural-language branch nuance used to choose between multiple stores in one city.
