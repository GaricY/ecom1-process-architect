# bp_product_discovery v0007

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-05-21T12:19:34+00:00`
- parent: `v0006`

## Rationale

On a catalogue claim verification ('a support note claims we stock <variant> in <family> with storage_type X AND color_family Y AND volume Z l, answer <NO> with the checked SKU if the extra catalogue claim is absent'), the Executor correctly determined no product in the family matched all three attributes and chose to cite the SKU matching attribute 1 (storage_type) and attribute 3 (volume), dropping the middle attribute (color). The grader required the SKU matching attribute 1 and attribute 2 (storage_type + color), dropping the last attribute (volume): the trial failed with 'answer missing required reference /proc/catalog/.../STO-<sku-matching-type+color>.json'. The existing v0006 covers count/availability shapes for product_discovery but says nothing about how to pick the 'checked SKU' for a multi-attribute claim verification when no product matches the full combination. This edit adds step 7 'Catalogue claim verification' with a deterministic longest-prefix-in-claim-attribute-order procedure: filter by attribute 1, then 1+2, then 1+2+3, etc., and cite the candidate set produced by the longest non-empty prefix; never skip an earlier claim attribute to match a later one. Matching anti-patterns name the exact grader error and call out the spurious-LIKE-substring pitfall the Executor also hit while exploring product_properties. The Refs section gains a matching bullet. Dependencies are unchanged in shape (still /docs/README.md, /AGENTS.MD, sql.help.txt, date.help.txt, id.help.txt) — sql.help.txt's 'why' is widened slightly to call out the product_properties / families / product_kinds tables that step 7 leans on.

## Rollback

Create a new version from v0006 content if the longest-prefix-in-claim-order rule causes Executors to under-cite catalogue rows on claim-verification tasks where the grader expected an alternative tie-break (e.g. citing all near-matches regardless of attribute order).

## Dependencies
- `workspace:/docs/README.md` — Source of the catalogue reporting rule and the dated-update folder list used by step 3 of the BP.
- `workspace:/AGENTS.MD` — Source of the reply-shaping rule 'availability answers reference only what is available'. Step 6 and the refs/anti-pattern bullets extend this rule from the answer message to refs.
- `bin_help:sql.help.txt` — Defines products / product_properties / families / product_kinds / inventory / stores table shapes. Step 7's claim-verification queries lean on product_properties(sku, key, value_text, value_number) and families.name / product_kinds.name; the prefix-narrowing rule is wrong if those shapes change.
- `bin_help:date.help.txt` — Step 3 makes /bin/date the only trusted source for the operating-day comparison on dated updates; the BP is wrong if /bin/date's contract changes.
- `bin_help:id.help.txt` — Step 1 calls /bin/id at session start; the BP's actor handling depends on its output shape.
