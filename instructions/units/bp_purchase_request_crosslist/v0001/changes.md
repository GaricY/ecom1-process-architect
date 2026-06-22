# bp_purchase_request_crosslist v0001

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-22T00:02:07+00:00`

## Rationale

New domain: /docs/purchase-request-crosslist.md defines a distinct deliverable (a competitor-OCR crosslist TSV) with a strict output schema, exact reason/match_status strings, and availability/fulfillable formulas. It reuses catalogue matching and branch availability but has its own report contract, so it is atomic as its own BP rather than overloading product_discovery or availability_and_inventory.

## Rollback

Remove the bp_purchase_request_crosslist unit and its render path and its bp_index route.

## Dependencies
- `workspace:/docs/purchase-request-crosslist.md` — Branch resolution, exact-match rule, spec-label/property-key mapping, the four reason strings, match_status values, formulas, and the exact column schema.
- `workspace:/docs/attachments.md` — /uploads as the root for the competitor OCR and crosslist TSV inputs.
- `bin_help:availability.help.txt` — Same-day availability used for available_today / fulfillable_qty.
- `sql_table:catalog` — Product name and properties for exact matching.
- `sql_table:locations` — Target branch is_open and inventory (on_hand/reserved).
