# bp_availability_and_inventory v0001

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-22T00:02:07+00:00`

## Rationale

New domain split out from product_discovery: /docs/availability-checks.md and the new /bin/availability tool define branch availability / stock-count / inventory-export as a distinct policy with its own same-day formula (max(on_hand-reserved,0)), incoming/due-within rules, and export schema. AGENTS.MD routes 'branch inventory, availability, or stock-count questions' here specifically.

## Rollback

Remove the bp_availability_and_inventory unit and its render path; fold branch availability back into product_discovery.

## Dependencies
- `workspace:/docs/availability-checks.md` — Same-day availability formula, incoming/due-within rules, read-only constraint, and inventory-export schema.
- `bin_help:availability.help.txt` — The /bin/availability tool and its max(on_hand-reserved,0) / missing-SKU-0 contract.
- `sql_table:locations` — Branch record and inventory rows (on_hand, reserved, incoming.arrival_in_days).
- `sql_table:catalog` — family_id and SKU set used to resolve products and build family exports.
