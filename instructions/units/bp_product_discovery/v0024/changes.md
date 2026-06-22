# bp_product_discovery v0024

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-22T12:13:05+00:00`
- parent: `v0023`

## Rationale

Owning layer: domain_policy (bp_product_discovery) — the matching method, not refs. Trial t007 asked 'how many products match powertools sizing calculator download, price below the ceiling — number only'; gold count is 1, the Executor answered 0. The Executor resolved the free-text request by concatenating each record's name/properties/hierarchy ids and requiring EVERY request word to be a literal substring (an AND over raw text). Only one record carried the literal token for the discriminating descriptor and it sat just over the price ceiling, so the conjunction collapsed to 0; genuine matches were dropped because the catalogue expresses the same concept with a different word (e.g. a 'quantity' calculator template) and via kind_id/family_id rather than the verbatim request token. This is a distinct facet from v0022/v0023, which only fixed which surviving records to cite on existence/count answers — they assume descriptors are already resolved to crisp predicates and never address how a bag-of-words request maps to catalogue fields, so this extends rather than re-adds a reverted rule. Fix (single focused edit, no new branch): in the existence/match/count branch step 1, instruct resolving each descriptor to the catalogue dimension it names (brand->brand, type/purpose word->kind_id/family_id/name, delivery/format word->the matching properties entry, price ceiling->price_cents) and treat a descriptor as satisfied when the relevant field denotes that concept — including via a synonym or a kind_id/family_id — rather than requiring a literal substring; plus one matching anti-pattern. The conjunction discipline ('match every requested spec'), the price-ceiling strictness, and the cite-only-the-surviving-cohort refs rule from v0023 are all preserved.

## Rollback

Create a new version from v0023 content if the descriptor-to-dimension matching rule over-broadens matches (e.g. starts counting synonym-only near-misses); that drops the step-1 mapping sentence and its anti-pattern while keeping the existence/match/count branch, refs scoping, and all other scenarios intact.

## Dependencies
- `workspace:/docs/catalogue-lookup.md` — Authorises resolving a request via product name, hierarchy fields, brand, prices, fulfillment type, return policy and properties — the source for mapping each descriptor to a catalogue dimension, and the clarify-and-cite-candidates rule the count branch distinguishes itself from.
- `workspace:/docs/attachments.md` — /uploads as the input root and the cross-check-against-canonical-records rule for the comparison-against-an-input scenario this BP still owns.
- `workspace:/AGENTS.MD` — The exactly-one-match SKU-lookup rule and the TRUE(1)/FALSE(0) yes/no token used for the existence verdict shape.
- `sql_table:catalog` — The descriptor-to-dimension rule names brand, kind_id, family_id, name, price_cents and properties as the fields the existence/count predicates test; schema drift on these columns would invalidate the match/near-miss rule.
- `bin_help:id.help.txt` — Actor identity pulled at session start (drives 'my' handling); contract change affects step 1 of the process.
