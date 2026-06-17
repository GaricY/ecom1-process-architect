# bp_identity_and_auth v0002

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-05-21T09:38:31+00:00`
- parent: `v0001`

## Rationale

Trial failed with 'answer missing required reference /proc/baskets/<id>.json' on a customer-actor denial. The Executor read /bin/id (customer), read the action-target basket, confirmed basket.customer_id == /bin/id user (own-record case), and still denied with policy-docs-only refs. Root cause: bp_identity_and_auth's 'Refs to set in scratchpad' section collapsed every customer-actor DENIED_SECURITY into 'policy docs only, no foreign /proc/...' — it gave no language for the customer-own-record capability-gap case (e.g. customer asks to perform an employee-only action on their own basket). bp_refs_and_submission v0002 already documents that case, but the narrower wording here misled the Executor. Fix: rewrite step 4 of the Process to call out the two distinct denial cases (cross-boundary vs. owned-record capability gap), expand the Refs section into three explicit branches (customer cross-boundary / customer own-record capability gap / employee capability gap), and add an explicit anti-pattern against collapsing every customer-actor denial into the cross-boundary case.

## Rollback

Create a new version from v0001 content (the original migration text) if this expanded refs-branching wording causes the Executor to over-include owned /proc records in cases where the ownership check did not actually pass.

## Dependencies
- `workspace:/docs/security.md` — Authoritative source for the identity/ownership policy this BP encodes — the cross-boundary rule, the 'customer can act only on records whose customer_id matches /bin/id user' clause, the legacy phrase glossary, the Identity Audit Phrases denial templates. If this doc moves or is reworded, the BP's wording and refs-branching may be stale.
- `bin_help:id.help.txt` — Defines the /bin/id output shape (user prefix, roles list) the actor-type and ownership branches in this BP read from. A change to that shape would invalidate the customer/employee/guest dispatch.
