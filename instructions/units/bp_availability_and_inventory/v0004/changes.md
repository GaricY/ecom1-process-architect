# bp_availability_and_inventory v0004

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-22T12:49:39+00:00`
- parent: `v0003`

## Rationale

Owning layer: topic_evidence (this BP's Step 4 + Evidence ledger). The FALSE verdict was accepted; the sole failure was a missing ref. The basket's third line was read from an uploaded OCR receipt whose SKU literal was a one-character garble of the live catalogue SKU. The Executor correctly resolved the line to that catalogue record but then dropped it from refs as a 'different SKU', so the grader flagged the missing /proc/catalog record. v0002 already made every request-named SKU's catalogue record mandatory (even at 0 availability) and v0003 deferred the answer token to submission_terminal -- both correct and retained; neither covered an OCR-garbled/mistyped handed-in SKU literal, so this widens the same cohort rule rather than unwinding a prior PA fix. The edit adds, to Step 4 and to answer_records / considered_not_cited / refs_must_include plus one anti-pattern, the rule that a handed-in basket/receipt/OCR line whose literal SKU matches no catalogue record is resolved to its real record by brand + name, availability is computed against the resolved SKU, and that resolved record is cited as the line's cohort member. Dependency note: the parent's sql_table:locations no longer resolves -- a world refresh renamed the branch family to 'stores' (this dump exposes TABLE stores and no locations), so the store-table dependency is updated to 'stores'; the shared executor-facing /proc/locations wording (identical across all sibling BPs) is intentionally left for a system-wide refresh sweep, not changed in this one-unit failure_fix.

## Rollback

Create a new version from v0003 content (which drops the OCR/typo-resolution clause from Step 4, the Evidence ledger, and the new anti-pattern) if requiring the resolved catalogue record over-cites.

## Dependencies
- `workspace:/docs/availability-checks.md` — Same-day availability formula (max(on_hand-reserved,0)), incoming/due-within rules, the read-only constraint, and the inventory-export schema this BP applies.
- `bin_help:availability.help.txt` — The /bin/availability contract (bare SKU strings, max(on_hand-reserved,0), missing-SKU-0); bare-SKU input is why each handed-in line must be separately resolved to a catalogue record before it can be cited.
- `sql_table:stores` — Branch record and inventory rows (on_hand, reserved, incoming.arrival_in_days) that drive same-day availability; the live family is 'stores' (the parent's 'locations' table was renamed by a world refresh and is absent from this dump).
- `sql_table:catalog` — Per-SKU catalogue record (/proc/catalog/<brand>/<sku>.json) used to resolve request-named SKUs -- including handed-in lines matched by brand + name after an OCR-garbled SKU literal -- and cited as cohort members; also drives family exports.
