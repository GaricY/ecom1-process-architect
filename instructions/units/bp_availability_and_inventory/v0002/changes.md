# bp_availability_and_inventory v0002

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-22T06:32:42+00:00`
- parent: `v0001`

## Rationale

Owning layer: topic_evidence (this topic BP's Evidence ledger). The count answer "1" was correct, but the grader required the /proc/catalog/<brand>/<sku>.json record for all six request-named SKUs (missing 6, extra 0). The ledger conditioned catalogue-record citation on whether 'the answer positively identifies' the SKU and routed '0 availability' SKUs to considered_not_cited, so the Executor cited none of the catalogue records. For a 'how many of these SKUs…' count, every enumerated SKU is a tested member of the answer cohort the count is computed over, including the five with 0 same-day availability. A secondary trigger: /bin/availability accepts bare SKU strings and never surfaces a catalogue path, so an Executor that only runs the tool never resolves the records to cite. The fix sharpens answer_records / considered_not_cited / refs_must_include so every request-named SKU's catalogue record is mandatory regardless of its availability, and adds a process step to resolve each named SKU to its /proc/catalog record. This restores consistency with bp_refs' existing answer_records cohort rule ('for list/count/cohort tasks, the answer cohort… not arbitrary examples') rather than broadening the shared refs model, so the edit stays in the narrow topic owner. v0001 is a world_refresh origin, not a prior PA fix, so this is not unwinding a regression.

## Rollback

Create a new version from v0001 content if requiring a catalogue ref for every request-named SKU over-cites (e.g. cites 0-availability SKUs the grader does not want).

## Dependencies
- `workspace:/docs/availability-checks.md` — Same-day availability formula, incoming/due-within rules, read-only constraint, and inventory-export schema that this BP's process and ledger encode.
- `bin_help:availability.help.txt` — The /bin/availability contract (bare SKU strings, max(on_hand-reserved,0), missing-SKU-0) the new 'resolve each named SKU to its catalogue record' step compensates for.
- `sql_table:locations` — Branch record and inventory rows (on_hand, reserved, incoming.arrival_in_days) that drive same-day availability.
- `sql_table:catalog` — Per-SKU catalogue record (/proc/catalog/<brand>/<sku>.json) now required as a citation for every request-named SKU; a schema change to this table would invalidate the new refs rule.
