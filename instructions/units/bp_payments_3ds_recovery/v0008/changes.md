# bp_payments_3ds_recovery v0008

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-28T18:31:46+00:00`
- parent: `v0007`

## Rationale

Schema rename touched this BP at one spot only: the refs anti-pattern that warns about the SQL cite-column lure now reads 'record_path' (was 'path'), keeping it consistent with the refreshed bp_refs section it cross-references. All gate logic reads JSON records (status, basket_id, three_ds.*) and quotes /docs/payments/3ds.md verbatim, none of which changed; the three_ds_* SQL columns were not renamed. No sql_table dependencies are added because the BP does not issue table queries.

## Rollback

Restore bp_payments_3ds_recovery v0007 content (the lone 'SQL path column' wording) if the record_path wording is judged unnecessary.

## Dependencies
- `workspace:/docs/payments/3ds.md` — Full gate set, legacy 3DS status table, forbidden actions, and the prerequisite line naming /docs/security.md and /docs/checkout.md.
- `workspace:/docs/checkout.md` — Prerequisite policy that 3DS recovery defers to; part of the ownership-matched three-doc refs bundle.
- `workspace:/docs/security.md` — Identity / cross-boundary rule named alongside checkout in the 3DS prerequisite line; cited on both the cross-boundary denial and the ownership-matched bundle.
- `bin_help:payments.help.txt` — Tool signature; this BP authorises recover-3ds only and excludes approve-refund/refund.
