# bp_identity_and_auth v0009

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-22T09:31:10+00:00`
- parent: `v0008`

## Rationale

Owning layer: topic_evidence on the identity gate (bp_identity_and_auth), not bp_discount. The Executor reached the correct verdict (employee actor lacks the required role -> OUTCOME_DENIED_SECURITY) but the grader failed it for a missing ref: the actor's own employee record (the /proc/employees/<actor>.json the role gate is decided from). The unit listed that record only as optional audit evidence ('only when read for...') and omitted it from refs_must_include; on a role-capability denial that stops at the role gate, the process never required it, so the Executor cited only the policy docs and the action target and dropped the role evidence. Fix: in step 6 and the Evidence ledger (actor_or_protocol_evidence, refs_must_include, anti-patterns) make the actor's own employee record mandatory decision evidence whenever an employee actor's verdict turns on that actor's role/store assignment, including a role-capability OUTCOME_DENIED_SECURITY where a later gate was never reached, scoped to the actor's own record (never another employee's record or a contact field to customers/guests). This is the shared identity invariant that fixes the class (discount, refund, payment, checkout role denials), so it belongs on the identity owner rather than the discount BP. Also corrects the stale employee-record family: the unit said /proc/staff and depended on sql_table:staff, but this world's family is /proc/employees (AGENTS.MD, /docs/discounts.md, and the schema all use it; there is no TABLE staff in the dump), so the /proc/staff references and the dependency are realigned to /proc/employees. No prior process_architect failure-fix touched this evidence rule (parents v0006-v0008 were a manual split and world_refreshes), so this is a new gap, not a regressing PA rule.

## Rollback

Create a new version from v0008 content (restoring the /proc/staff wording and the optional 'only when read for' employee-record evidence line) if requiring the actor's own employee record on role-capability denials proves to over-include refs.

## Dependencies
- `workspace:/docs/security.md` — Sole authority for identity, ownership, cross-boundary rule, capability-vs-boundary distinction, employee-contact privacy, and the legacy phrase glossary the role/identity gate encodes.
- `workspace:/docs/employees.md` — Employee accounts cannot perform customer operations -> the actor-kind unsupported branch in step 7/outcomes.
- `bin_help:id.help.txt` — Defines the /bin/id user/roles output shape this BP branches on to classify the actor and decide the role gate.
- `sql_table:employees` — Backs the actor's /proc/employees/<id>.json roles[]/title/store_id; the role/store gate and the new role-capability-denial evidence rule are read from this family, so a shape change makes the rule stale. Replaces the absent sql_table:staff.
