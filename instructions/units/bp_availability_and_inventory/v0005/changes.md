# bp_availability_and_inventory v0005

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-22T14:24:57+00:00`
- parent: `v0004`

## Rationale

Owning layer: topic_evidence (this BP's process step + Evidence ledger). t042 produced two extra /proc/catalog refs: PT-...-216 (the named exclusion) and PT-...-160 (a smaller family sibling). The conflicting bp_refs v0014 already fixes the named-exclusion mis-citation at the shared refs layer (the Executor cited -216 because v0013 told it 'named exclusions must be cited'; v0014 narrows that), so I dropped my bp_refs edit as subsumed. But v0014 does NOT fix the -160 citation: the request DESCRIBES one product by a comparative descriptor ('larger blade pack', diameter unstated) rather than enumerating SKUs, and this BP never had a described-product resolution step, so the Executor treated both non-excluded family members {-160, -190} as the answer cohort instead of resolving 'larger' to the single matching SKU. This is the topic owner, not refs. I extend v0004 rather than replace it: v0004's OCR-garbled handed-in-line rule is correct and orthogonal (it ADDS resolved lines to an enumerated cohort); the described-product case NARROWS a scanned family to the one matching SKU and demotes the failing siblings and the named exclusion to rejected candidates. I add a new Step 5 (resolve a described product to its matching SKU(s) via family `properties`; the cohort is exactly the resolved SKU(s); siblings failing the descriptor and a SKU named only to exclude it are rejected candidates, never cited) plus matching answer_records / considered_not_cited / refs_must_include / refs_must_not_include bullets and one anti-pattern, reusing the existing 'a disqualified product is never cited' invariant from bp_product_discovery. This preserves v0002's enumerated-SKU cohort rule, v0003's token-defer rule, and v0004's OCR rule unchanged. Dependency note: I declare sql_table:locations, not sql_table:stores — v0004's changes.md asserted a world refresh renamed the table to 'stores', but this trial dump's bin-help/sqlite_schema.txt exposes TABLE locations (and no TABLE stores) and the Executor's live reads used /proc/locations/..., so locations is the table that actually resolves against this dump.

## Rollback

Create a new version from v0004 content (drops the described-product resolution Step 5 and its ledger/anti-pattern bullets) if resolving a comparative descriptor to a single SKU under-cites where the grader actually wanted the full family cohort.

## Dependencies
- `workspace:/docs/availability-checks.md` — Same-day availability formula, incoming/due-within rules, read-only constraint, and the inventory-export schema this BP's process and ledger encode.
- `bin_help:availability.help.txt` — The /bin/availability contract (bare SKU strings, max(on_hand-reserved,0), missing-SKU-0) that forces resolving SKUs to catalogue records for citation, including resolving a described product to the matching SKU(s).
- `sql_table:locations` — Branch record and inventory rows (on_hand, reserved, incoming.arrival_in_days) that drive same-day availability; TABLE locations is the branch family present in this trial dump's sqlite_schema.txt.
- `sql_table:catalog` — Per-SKU catalogue record (/proc/catalog/<brand>/<sku>.json), including `properties`, used to resolve a described product by comparative descriptor and to cite the resolved SKU(s); schema drift would invalidate the new resolution rule.
