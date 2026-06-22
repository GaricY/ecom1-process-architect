# bp_product_discovery v0023

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-22T09:45:19+00:00`
- parent: `v0022`

## Rationale

Owning layer: topic_evidence (bp_product_discovery). My trial was a count / attribute-filter query ('how many SKUs match Aircraft Compact-Air 240 compressor, without accessory bundle, tank size not supplied, under EUR 152.20 — number only'). The Executor's scratchpad correctly classified the price-excluded /24 and the accessory-set /SET as excluded and computed count=1, but still cited all three /proc/catalog records, so the grader flagged the two filter-excluded candidates as extra refs (0.0%). While I drafted, another PA landed v0022 adding a 'Product existence / match query' branch for the same root-cause family — filter the candidate cohort against the whole requested spec and cite only the records that satisfy every spec; near-misses stay considered_not_cited. v0022 captures the root cause but scopes it to the yes/no existence answer shape: it does not name the count answer shape (a number, possibly >1, where the whole surviving cohort must be cited), nor the price-ceiling / exclusion-phrase filters, nor the 'an unsupplied attribute is not a filter' rule, and a count query phrased 'how many ... number only' would not obviously match its existence-only trigger. So this is an extension, not a replacement and not subsumed. I generalised v0022's branch in place into one 'Product existence / match / count query' branch covering both the yes/no and count answer shapes under one filtering+refs rule (refs = exactly the surviving cohort; rejected/near-miss/filter-excluded = considered_not_cited; zero-result cites nothing), folding in the price-ceiling/exclusion predicates and the 'do not invent an unsupplied filter' and 'not the clarification branch' points, and updated the When-applies line, Outcomes, Evidence ledger and anti-patterns to match. This is a single coherent edit, not two stacked patches: the claim-verification cite-the-base-SKU rule is preserved. bp_refs v0012 already holds the shared invariant ('the answer cohort or aggregate evidence, not arbitrary examples'), so this stays a topic scenario, not a refs_safety change.

## Rollback

Create a new version from v0022 content if the unified existence/match/count branch mis-scopes refs; that reverts to v0022's existence-only branch and drops the count answer shape and the price-ceiling/exclusion/'do not invent a filter' lines, leaving SKU-lookup, claim-verification, and comparison scenarios untouched.

## Dependencies
- `workspace:/docs/catalogue-lookup.md` — Catalogue resolution fields and the clarify-and-cite-candidate-SKUs rule that the existence/match/count branch must distinguish itself from (filters are explicit, so excluded candidates are rejected, not unresolved).
- `workspace:/docs/attachments.md` — /uploads as the input root and the cross-check-against-canonical-records rule for the comparison-against-an-input scenario this BP still owns.
- `workspace:/AGENTS.MD` — The exactly-one-match SKU-lookup rule and the TRUE(1)/FALSE(0) yes/no token used for the existence verdict shape.
- `sql_table:catalog` — Product price_cents, name, and properties are the fields the existence/count filter predicates (price ceiling, bundle exclusion, property match) operate on; schema drift would invalidate the match/near-miss rule.
- `bin_help:id.help.txt` — Actor identity pulled at session start (drives 'my' handling); contract change affects step 1 of the process.
