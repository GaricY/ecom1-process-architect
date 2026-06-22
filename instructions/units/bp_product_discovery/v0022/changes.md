# bp_product_discovery v0022

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-22T06:38:20+00:00`
- parent: `v0021`

## Rationale

The trial was a product existence query ("Customer wants '<full spec incl. battery platform Stihl AK>'. Does such product exist?"). The whole description is one conjunctive search filter; no catalogue record satisfies all specs (the only matching kit is on battery_platform 'Bosch 18V Power for All', not the requested platform), so the verdict is FALSE and no record is a match. The grader expected empty /proc/catalog refs but the Executor cited the near-miss record (extra ref → 0.0%). Root cause is topic_evidence: the BP only had a claim-verification branch, which cites the pre-identified base SKU even on a negative verdict, and the Executor over-applied it to an existence query. Fix (owning layer bp_product_discovery): add a distinct 'Product existence / match query' branch that cites a /proc/catalog record only when it satisfies every requested spec and cites nothing on a 'does not exist' verdict (near-misses stay considered_not_cited, mirroring the existing availability rule), plus a guard distinguishing it from claim verification, and matching Evidence-ledger / anti-pattern entries. This adds a missing branch rather than re-introducing a reverted rule; the claim-verification cite-the-base-SKU rule from v0019/v0020 is preserved and now scoped to pre-identified products.

## Rollback

Create a new version from v0021 content (drops the 'Product existence / match query' branch and its ledger/anti-pattern lines) if the new branch wrongly suppresses needed refs on existence answers.

## Dependencies
- `workspace:/docs/catalogue-lookup.md` — Defines how a catalogue request resolves to candidate records (name/hierarchy/brand/price/properties) and the clarify-and-cite rule the match-narrowing in the existence branch relies on.
- `workspace:/docs/attachments.md` — Source for the /uploads input root and cross-check-against-canonical-records rule that the comparison-against-an-input branch (retained in this unit) depends on.
- `workspace:/AGENTS.MD` — Source of the exactly-one-match SKU-lookup rule and the TRUE(1)/FALSE(0) yes/no token used for the existence verdict shape.
- `sql_table:catalog` — The record fields/properties (e.g. battery_platform) are what decide whether a record satisfies every requested spec; a schema change to catalog could invalidate the match/near-miss rule.
- `bin_help:id.help.txt` — Actor identity pulled at session start (drives 'my' handling); contract change affects step 1 of the process.
