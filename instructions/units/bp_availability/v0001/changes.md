# bp_availability v0001

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-30T09:37:50+00:00`

## Rationale

A dedicated branch-availability domain now exists: AGENTS.MD routes 'branch inventory, availability, or stock-count questions' to the new /docs/availability-checks.md, and a new /bin/availability tool computes same-day availability max(on_hand-reserved,0). The doc also defines an inventory-export sub-workflow (per family, write a report file). This is a distinct domain boundary (dedicated doc + dedicated tool + export-write behavior) split out of bp_product_discovery rather than an extension, keeping each BP atomic.

## Rollback

Remove bp_availability from the registry and bp_index routing, and fold branch availability/inventory/export back into bp_product_discovery.

## Dependencies
- `workspace:/docs/availability-checks.md` — Same-day availability formula, missing-SKU rule, incoming-stock + due-within rules, read-only guarantee, and the inventory-export contract.
- `bin_help:availability.help.txt` — availability <store_record_path|-> <sku>... ; max(on_hand-reserved,0), missing SKU -> 0.
- `bin_help:jq.help.txt` — JSON read tool for store/inventory/incoming/catalog rows now that /bin/sql is unavailable.
- `bin_help:cat.help.txt` — Raw record read tool for inventory JSON.
- `bin_help:date.help.txt` — Used when the request imposes a date/window or future-date export columns.
- `sql_table:location_inventory` — on_hand/reserved per (store_id, sku) for same-day availability.
- `sql_table:location_inventory_incoming` — arrival_in_days/quantity for incoming stock and export future-date columns.
- `sql_table:locations` — Branch record and record_path for the queried store.
- `sql_table:catalog` — family_id enumeration and SKU records for exports.
