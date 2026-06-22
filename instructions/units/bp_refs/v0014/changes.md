# bp_refs v0014

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-22T12:38:49+00:00`
- parent: `v0013`

## Rationale

Owning layer: refs_safety (shared request-named-input class), and this is a PA regression to narrow rather than a new patch. The verdict (FALSE/OK) and availability math were correct; the only grader failure was a /proc/catalog refs mismatch — extra [PT-SND-BOS-GEX125-DUST.json], missing []. The request named that SKU only as an exclusion ('but not <id>') to disambiguate which discs accessory set was meant (CASE vs DUST); DUST's own inventory never entered the answer, so the grader treats it as a rejected candidate, not a citation. bp_refs v0013 was created by process_architect for this exact catalog-exclusion family on the OPPOSITE failure (DUST missing) and added a blanket invariant that ANY request-named exclusion, 'including ... which candidate you selected,' is decision evidence and must be cited. The Executor's scratchpad shows it cited DUST explicitly as a 'request-named exclusion,' i.e. it followed v0013 verbatim. v0013 over-generalised by sweeping pure product-disambiguation into the cite rule. The fix narrows the rule to the genuine distinction (which bp_product_discovery already encodes for filter-excluded near-misses): cite a request-named id only when its OWN facts enter the answer — a reported cohort member, or a value subtracted from / bounding the reported aggregate — and keep a record named only to pick which other record the answer is about in considered_not_cited, uncited. This preserves the legitimate subtraction/scope-bound case v0013 targeted while fixing the disambiguation case. Cross-unit consistency checked: bp_availability_and_inventory cites only a 'tested member of the count/verdict' (DUST is not tested), and bp_submission_terminal delegates include/exclude to refs.md/topic BP, so no sibling drift.

## Rollback

Create a new version from v0013 content if narrowing causes under-citation of request-named exclusions; that restores the blanket 'any named exclusion / candidate selection must be cited' rule.

## Dependencies
- `workspace:/docs/security.md` — Cross-boundary and employee-contact-detail prohibition still gates whether any request-named record identifier is safe to cite; the narrowed cite/don't-cite rule must defer to it.
- `workspace:/AGENTS.MD` — Grounding rule ('ground every referenced object in its live path') and the clarification 'cite every candidate' rule that the request-named-identifier citation taxonomy rests on.
