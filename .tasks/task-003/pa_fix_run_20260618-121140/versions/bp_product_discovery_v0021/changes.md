# bp_product_discovery v0021

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-18T09:37:07+00:00`
- parent: `v0020`

## Rationale

On a comparison-against-an-input task ('look at the old receipt; if we sold these products today would the total excl. VAT stay within 3 EUR?'), the Executor read an OCR'd receipt, matched 3 of 4 line SKUs exactly via SQL, and on the 4th SKU (an OCR-corrupted token that returned zero rows on exact `product_sku` match and zero on literal `search`) concluded the product was 'not in the catalogue' and answered <NO>. The expected answer is <YES>: the 4th product still exists and today's full-basket total stays within tolerance, so the SKU token was simply mangled by OCR. The BP's comparison section told the Executor to map each line by SKU but never warned that a scanned/OCR'd input's identifier tokens are unreliable, nor required re-resolving an unmatched line by the name + brand/series/model + unit price the document also prints before declaring a product gone. This edit adds that tolerant-reconciliation step and a matching anti-pattern so one unmatched OCR'd SKU no longer flips a within-tolerance comparison to the negative answer.

## Rollback

Create a new version from v0020 content if the OCR-tolerant reconciliation rule causes Executors to over-match unrelated catalogue rows by name/price.

## Dependencies
- `bin_help:date.help.txt` — Trusted date provider used when product count/update handling invokes policy_update_scan.
- `bin_help:id.help.txt` — Actor identity pulled at session start (drives 'my' handling).
- `sql_table:product_variants` — Public product facts and canonical catalogue record_path; the new reconciliation rule re-resolves an OCR-mangled line via this table's brand/series/model/product_name/price_cents columns.
- `sql_table:product_variant_properties` — Per-SKU property rows (product_sku, property_key, property_value_*) used for claim verification.
- `sql_table:product_families` — Family/brand/model grouping used to identify products, including when matching a line by brand/series/model.
- `sql_table:product_kinds` — product_kind_id and product-kind scope for count questions.
- `sql_table:store_inventory` — Store/SKU availability source: available_today_quantity keyed by (store_id, product_sku).
- `sql_table:stores` — Public store ids, record_path cite paths, city nuance targets, and open status.
- `workspace:/proc/stores/README.md` — Natural-language branch nuance used to choose between multiple stores in one city.
