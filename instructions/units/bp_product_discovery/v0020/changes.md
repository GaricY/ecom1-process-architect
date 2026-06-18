# bp_product_discovery v0020

- mode: `manual_refactor`
- created_by: `human`
- created_at: `2026-06-18T09:04:42+00:00`
- parent: `v0019`

## Rationale

Separate product-discovery domain verdicts and required answer identifiers from generic terminal payload formatting. Claim verification now records the verdict and required identifier/path payload for submission_terminal instead of restating yes/no token rules or concrete submit message examples.

## Rollback

Retire this version to fall back to v0019 if the terminal delegation weakens product claim-verification payload requirements.

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
