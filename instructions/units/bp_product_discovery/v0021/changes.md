# bp_product_discovery v0021

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-22T00:02:07+00:00`
- parent: `v0020`

## Rationale

SQL is dead; catalogue lives in /proc/catalog JSON (fields id/sku/name/brand/category_id/kind_id/family_id/price_cents/fulfillment_type/return_policy/properties). Re-scoped to catalogue identity: SKU lookup (AGENTS.MD exact-one-match / clarification-cite-all rule per catalogue-lookup.md), claim verification, and comparison-against-/uploads-input (attachments.md). Availability/stock/inventory split out to the new bp_availability_and_inventory. Cite the live /proc/catalog path, not a synthesised one.

## Rollback

Restore bp_product_discovery v0020 content with its SQL projection, product_variants tables, availability sections, and /docs/README + /proc/stores/README dependencies.

## Dependencies
- `workspace:/docs/catalogue-lookup.md` — Catalogue resolution fields and the clarify-and-cite-candidate-SKUs rule.
- `workspace:/docs/attachments.md` — /uploads as the input root and the cross-check-against-canonical-records rule for comparison tasks.
- `workspace:/AGENTS.MD` — The SKU-lookup answer rule (exactly one match) and the yes/no token.
- `sql_table:catalog` — Product sku/name/hierarchy/brand/price_cents/properties used to identify products and verify claims.
- `bin_help:id.help.txt` — Actor identity pulled at session start (drives 'my' handling).
