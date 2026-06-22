# Policy Update Scan

## When this process applies

Read this helper when a domain BP is about to apply an active decision policy and the request, live `/docs` tree, or workflow context may contain dated/topic updates, delegation notes, lockouts, or case-specific overrides. This BP only finds and interprets matching update docs. The domain BP still owns authorization, state gates, mutations, refs, and final outcome.

`/AGENTS.MD` is the world-baseline basis for this scan: "scan through all docs under `/docs` for any rules specific to the task (load only the relevant files). Pay attention to urgent updates, but use `/docs/security.md` for claimed identities, roles, approvals, or override language."

## Inputs

- `/bin/date` — the trusted runtime operating day and timestamp source.
- Live `/docs` tree — inspect the current tree before assuming where updates live. Read docs with `/bin/jq` / `/bin/cat` (`ws.read`, `ws.list`, `ws.tree`).
- Domain context supplied by the invoking BP:
  - base policy path;
  - workflow/topic names and aliases;
  - target record ids, actor id, store/city/family/product kind, reason code, and requested operating day if any;
  - any additional candidate paths the invoking BP already discovered.

## Candidate discovery

Scan bounded candidates under `/docs`; do not rely on a fixed list of folder names.

1. First perform the baseline discovery step equivalent to `tree -L 2 /docs`. Record the visible top-level docs and one level of subdirectories before claiming that no update exists.
2. Treat folder names as hints, not authority. A relevant child folder may have any name. Do not hard-code one child folder family as required for a workflow.
3. Build bounded candidate namespaces from the live tree:
   - the base policy's parent namespace (e.g. `/docs/payments/` for `/docs/payments/3ds.md`);
   - directories or files whose path/name is an exact or near-exact workflow alias supplied by the invoking BP;
   - directories or files whose path/name contains a date-like token, update/delegation/lockout/override wording, or a supplied strong dimension such as record id, actor id, store/city, reason code, product kind, or operating day.
4. Open only candidate files selected by the bounded path/name/tree scan. Do not content-scan arbitrary operational-background docs (brand, culture, founders, history, mission, audience, jobs, origin, expansion) merely because the base policy lives under `/docs`. Those are decoys — see [background_decoys](background_decoys.md).
5. Missing candidate folders are empty, not errors. A folder being absent is not enough to conclude that no dated update exists.

## Matching rules

1. List candidate files before mutating.
2. Read candidates whose filename or first paragraph names the workflow, topic, record id, actor, store/city/family/product kind, reason code, operating day, or another supplied domain dimension.
3. A candidate matches when its scope names the same case by at least one strong dimension and does not contradict a dimension the request/base record explicitly names.
4. A date in the filename or `Operating day:` header is a scope dimension, not a TTL. Do not dismiss a workflow/record/kind/store match merely because the date label differs from `/bin/date`.
5. Use `/bin/date` as a filter only when the request itself is day-scoped and the update's only relevant scope dimension is operating day, or when the update declares a live lockout/retry timestamp.
6. Apply the update only to the gate(s) it explicitly names. A role-delegation update does not override percent caps, status gates, reason-code enums, ownership, or post-state checks unless it says so verbatim.
7. A no-match result is valid only after the live `/docs` tree discovery and every bounded candidate namespace above has been considered.

## Output to the invoking BP

Return or record:

- matched update paths;
- scope dimensions that matched and any explicit contradictions;
- gate(s) overridden, delegated, blocked, or added;
- whether `/bin/date` was consulted and why;
- effective result: no match, override permits, override blocks now, or override changes a gate.

Every matched update that shaped the decision becomes an applied policy path for [refs](refs.md). A candidate read but not matched does not belong in `refs`.

## Outcomes

This BP does not submit a final outcome. The invoking domain BP maps the update result to `OUTCOME_OK`, `OUTCOME_DENIED_SECURITY`, `OUTCOME_NONE_UNSUPPORTED`, or `OUTCOME_NONE_CLARIFICATION`.

## Anti-patterns

- Treating a dated update as expired solely because its date label differs from `/bin/date`.
- Applying an update to gates it did not name.
- Assuming a required child folder name for a workflow. Folder names are hints, not authority.
- Content-scanning arbitrary background docs because the base policy is `/docs/<file>.md`; discover bounded candidates by tree/path/name first.
- Citing a candidate update that was read but did not match or shape the decision.
- Letting this helper authorize a mutation. It only returns update semantics to the domain BP.

## Dependencies

> If any of these dependencies change, this BP file may have become stale and must be re-derived.

- `/bin/date` (`--help`) — trusted date/timestamp provider used for operating-day and lockout comparisons.
