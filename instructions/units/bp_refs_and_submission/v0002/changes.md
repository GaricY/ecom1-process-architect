# bp_refs_and_submission v0002

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-05-21T06:54:18+00:00`
- parent: `v0001`

## Rationale

Executor was a customer actor (cust_*) asked to perform an employee-only mutation (apply a basket discount) on the customer's own basket. The basket's customer_id matched ws.id().user, so this was an own-record / capability-gap case, not a cross-boundary case. Executor correctly returned OUTCOME_DENIED_SECURITY (customer lacks discount_manager) but dropped /proc/baskets/<id>.json from refs because the unit's customer-actor section only described the cross-boundary rule (refs = policy-docs only). The grader rejected the answer with 'answer missing required reference /proc/baskets/<id>.json'. Fix: add an explicit 'Customer-actor own-record exception' that mirrors the existing employee-actor exception — when record.customer_id == ws.id().user, the action target stays in refs even on capability-gap denial — and rewrite the actor-type branching and pre-submission checklist so ownership is checked before deciding refs.

## Rollback

Create a new version from v0001 content if the added own-record exception turns out to broaden refs incorrectly (e.g. graders treat customer's own /proc paths as cross-boundary in some flow we missed).

## Dependencies
- `workspace:/docs/security.md` — Authoritative source for the cross-boundary rule, ownership rule (customer can act only on records whose customer_id matches /bin/id), and Identity Audit Phrases the denial wording draws from. The new own-record vs cross-boundary branching cites this doc directly.
- `workspace:/docs/README.md` — Document Families split — decides which /docs/* are active decision policies eligible for refs vs operational background that must be excluded. The 'What to include / NOT to include in refs' sections depend on this taxonomy.
- `bin_help:id.help.txt` — Defines the shape of ws.id() output (user prefix cust_* vs emp_*, roles list) that the actor-type branching and pre-submission checklist key off.
