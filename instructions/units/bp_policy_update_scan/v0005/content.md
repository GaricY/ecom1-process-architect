# Policy Update Scan

## When this process applies

Read this helper when a domain BP is about to apply an active decision policy and the request, live `/docs` tree, or workflow context may contain urgent/dated updates, addenda, lockouts, or case-specific overrides. `/AGENTS.MD` directs the executor to "Pay attention to urgent updates, but use `/docs/security.md` for claimed identities, roles, approvals, or override language." This BP only finds and interprets matching update docs; the domain BP still owns authorization, state gates, mutations, refs, and the final outcome.

## Inputs

- `/bin/date` — the trusted runtime operating day and timestamp source.
- Live `/docs` tree — inspect the current tree before assuming where updates live.
- Domain context supplied by the invoking BP:
  - base policy path;
  - workflow/topic names and aliases;
  - target record ids, actor id, store/city/family/product kind, reason code, and requested operating day if any;
  - any candidate paths the invoking BP already discovered.

## Candidate discovery

Scan bounded candidates under `/docs`; do not rely on a fixed list of folder names.

1. First perform a baseline tree scan of `/docs` (e.g. `ws.tree("/docs", level=2)` or `ws.list`). Record the visible top-level docs and one level of subdirectories before claiming no update exists.
2. Treat folder names as hints, not authority. A relevant child folder may have any name; do not hard-code one child folder family as required for a workflow.
3. Build bounded candidate namespaces from the live tree:
   - the base policy's parent namespace (e.g. `/docs/payments/` for `/docs/payments/3ds.md`);
   - files/directories whose path/name is an exact or near-exact workflow alias supplied by the invoking BP;
   - files/directories whose path/name contains a date-like token, update/addendum/lockout/override wording, or a supplied strong dimension (record id, actor id, store/city, reason code, product kind, operating day).
4. Open only candidate files selected by the bounded path/name/tree scan. Do not content-scan arbitrary background/culture docs merely because the base policy lives under `/docs`.
5. Missing candidate folders are empty, not errors.

## Matching rules

1. List candidate files before mutating.
2. Read candidates whose filename or first paragraph names the workflow, topic, record id, actor, store/city/family/product kind, reason code, operating day, or another supplied dimension.
3. A candidate matches when its scope names the same case by at least one strong dimension and does not contradict a dimension the request/base record explicitly names.
4. A date in a filename or `Operating day:` header is a scope dimension, not a TTL. Do not dismiss a workflow/record/kind/store match merely because the date label differs from `/bin/date`.
5. Use `/bin/date` as a filter only when the request itself is day-scoped and the update's only relevant scope dimension is operating day, or when the update declares a live lockout/retry timestamp.
6. Apply the update only to the gate(s) it explicitly names. It does not override caps, status gates, reason-code enums, ownership, role requirements, or post-state checks unless it says so verbatim — and it cannot grant a role the base policy reserves (e.g. `discount_manager`).
7. A no-match result is valid only after the live `/docs` tree discovery and every bounded candidate namespace has been considered.

## Output to the invoking BP

Return or record: matched update paths; scope dimensions that matched and any explicit contradictions; gate(s) overridden, delegated, blocked, or added; whether `/bin/date` was consulted and why; the effective result (no match, override permits, override blocks now, override changes a gate). Every matched update that shaped the decision becomes an applied policy path for [refs](refs.md). A candidate read but not matched does not belong in `refs`.

## Evidence ledger

`policy_docs_applied`:

- Matched update/addendum/lockout docs whose text shaped a gate, scope, date comparison, mutation/no-mutation, count formula, or denial.

`considered_not_cited`:

- Candidate update docs read but not matched.
- Candidate folders listed but absent or empty.

`refs_must_include` (for the invoking BP):

- Every matched update path that shaped the final decision, copied verbatim as a live `/docs/...` path.

`refs_must_not_include` (for the invoking BP):

- Candidate paths only rejected, stale for the case, contradictory, or outside the bounded scan.

## Outcomes

This BP does not submit a final outcome. The invoking domain BP maps the result to `OUTCOME_OK`, `OUTCOME_DENIED_SECURITY`, `OUTCOME_NONE_UNSUPPORTED`, or `OUTCOME_NONE_CLARIFICATION`.

## Anti-patterns

- Treating a dated update as expired solely because its date label differs from `/bin/date`.
- Applying an update to gates it did not name, or letting it grant a role/cap the base policy reserves.
- Skipping the live `/docs` tree discovery and assuming a required child-folder name for a workflow.
- Content-scanning arbitrary background/culture docs because the base policy is `/docs/<file>.md`.
- Citing a candidate update that was read but did not match or shape the decision.
- Letting this helper authorize a mutation — it only returns update semantics to the domain BP.

## Dependencies

> If any of these dependencies change, this BP file may have become stale and must be re-derived.

- `/bin/date` (`--help`) - trusted date/timestamp provider used for operating-day and lockout comparisons.
