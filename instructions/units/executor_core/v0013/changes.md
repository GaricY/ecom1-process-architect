# executor_core v0013

- mode: `failure_fix`
- created_by: `human`
- created_at: `2026-05-28T23:18:30+00:00`
- parent: `v0012`

## Rationale

Remove benchmark-schema specifics from executor_core, which world_refresh is forbidden to touch, so they cannot rot silently on DB drift. (1) The SQL examples used pre-drift table/column names — `SELECT sku, path FROM products WHERE family_id = 7`, `FROM payments ORDER BY id`, and prose `product_properties`/`value_text`/`families.name` — none of which exist post-rename (real: product_variants/product_family_id/product_sku/record_path, payment_transactions, product_variant_properties/property_value_text, product_families). Replaced with abstract placeholders (some_table/col_a/some_fk/some_id) plus an explicit 'read real names from bin-help/sqlite_schema.txt; never copy these' note. This is the seed of opus-4-8 t05 (run 20260529-002118): its first query `FROM products JOIN families` raised `no such table: products`, after which it fabricated the SKU/record_path and submitted (missing the real /proc/catalog/STO-12JLHT7D.json ref). (2) The `## Mutation preflight` section hard-coded a mutator->file list that had already gone stale (3 tools vs 5 in bp_index section-4); replaced with a redirect to the new bp_index `Mutating` column. Dependency contract unchanged (prose-only).

## Rollback

Revert to v0012 if executors regress on SQL call-shape guidance with abstract placeholders (e.g. start emitting literal `some_table`); if so, keep the placeholders but add one worked example that explicitly reads names from the schema file first, rather than restoring pre-drift table names.
