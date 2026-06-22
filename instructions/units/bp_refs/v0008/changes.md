# bp_refs v0008

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-30T09:37:50+00:00`
- parent: `v0007`

## Rationale

All cited SQL tables were renamed and customer_accounts was removed; /proc/README.md was removed so record families/path conventions come from the schema; with /bin/sql down there is no SQL record_path column to copy, so refs are the live /proc path read via /bin/jq|cat; the topic-doc table adds availability/dispatch/catalogue-lookup and updates the refund tool; /uploads input-artifact grounding now cites /docs/attachments.md; public product/store paths resolve to /proc/catalog and /proc/locations.

## Rollback

Restore v0007 content (old SQL table list incl. customer_accounts, /proc/README.md, SQL record_path-column language, old topic-doc table with /bin/payments refund routing).

## Dependencies
- `workspace:/docs/security.md` — Cross-boundary rule and personal-information disclosure boundary.
- `workspace:/docs/attachments.md` — Defines /uploads as the request-named input-artifact root for class-1 grounding.
- `bin_help:id.help.txt` — Actor output shape for customer/employee/guest branching.
- `sql_table:carts` — Customer ownership, store pointer, status, and basket record path.
- `sql_table:payment_ledger` — Customer ownership, basket/store pointers, status, and payment record path.
- `sql_table:return_workflows` — Customer ownership, payment pointer, status, and return record path.
- `sql_table:catalog` — Public catalogue product record path and SKU fields.
- `sql_table:locations` — Public store record path and location fields.
- `sql_table:staff` — Employee contact/profile records that are private by default.
