# bp_refs_and_submission v0003

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-05-21T09:43:37+00:00`
- parent: `v0002`

## Rationale

Executor was a customer actor (cust_*) asked to apply a basket discount on their own basket (own-record case). The request also asked the executor to first 'confirm' the manager for a specific named store. Executor correctly denied at the capability gate (customer lacks discount_manager) and correctly kept the own basket in refs, but dropped /proc/stores/<basket.store_id>.json — the public store record that the request named (by store display name) and that the discount policy's manager-store-match gate would have read. The grader rejected with 'answer missing required reference /proc/stores/<id>.json'. v0002 already says public records 'may always appear' but does not require them; the executor read that as permissive. Fix: promote 'public records named or implicated by the request' from optional to required in every actor/ownership branch, add a 'Public-record sweep' step to the pre-submission checklist, expand the own-record exception example to include the store, and add an anti-pattern entry for dropping such public records. Generalises across discount (basket.store_id), checkout (basket_lines[*].sku), and any future request that names a store/SKU.

## Rollback

Create a new version from v0002 content if the promoted public-record rule turns out to over-include (e.g. graders flag refs containing stores/SKUs the request did not actually lean on).

## Dependencies
- `workspace:/docs/security.md` — Authoritative source for the cross-boundary rule, ownership rule, and Identity Audit Phrases the denial wording draws from. The actor-type / ownership branching cites this doc directly.
- `workspace:/docs/README.md` — Document Families split — decides which /docs/* are active decision policies eligible for refs vs operational background that must be excluded. The 'What to include / NOT to include in refs' sections key off this taxonomy.
- `bin_help:id.help.txt` — Defines the shape of ws.id() output (user prefix cust_* vs emp_*, roles list) that the actor-type branching and pre-submission checklist key off.
