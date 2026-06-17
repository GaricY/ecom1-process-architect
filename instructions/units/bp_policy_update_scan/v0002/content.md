# Policy Update Scan

## When this process applies

Read this helper when a domain BP is about to apply an active decision policy and the request, docs tree, or topic folder may contain dated/topic updates, addenda, lockouts, delegation notes, or case-specific overrides. This BP only finds and interprets matching update docs. The domain BP still owns authorization, state gates, mutations, refs, and final outcome.

## Inputs

- `/bin/date` - the trusted runtime operating day and timestamp source.
- Domain context supplied by the invoking BP:
  - base policy path and, when applicable, a narrow topic folder;
  - workflow/topic names and aliases;
  - target record ids, actor id, store/city/family/product kind, reason code, and requested operating day if any;
  - candidate-location constraints that keep the scan bounded for that domain.

## Candidate locations

Scan only bounded candidates under `/docs`:

- The topic policy's own folder when it is a narrow subfolder. Example: for `/docs/payments/3ds.md`, scan siblings under `/docs/payments/` and exclude the base file itself.
- Cross-workflow update folders named by the world baseline, commonly `/docs/current-updates/`, `/docs/policy-updates/`, `/docs/ops-policy-notes/`, and `/docs/catalogue-addenda/`.
- Additional candidate folders only when the invoking BP explicitly names them from the live workspace.

If the base policy lives directly under `/docs` (for example `/docs/discounts.md`), do not scan the whole `/docs` root as a topic-sibling folder. Use the cross-workflow update folders and any narrower domain-specified folder instead.

Missing folders are empty, not errors.

## Matching rules

1. List candidate files before mutating.
2. Read candidates whose filename or first paragraph names the workflow, topic, record id, actor, store/city/family/product kind, reason code, operating day, or another domain dimension supplied by the invoking BP.
3. A candidate matches when its scope names the same case by at least one strong dimension and does not contradict a dimension the request/base record explicitly names.
4. A date in the filename or `Operating day:` header is a scope dimension, not a TTL. Do not dismiss a workflow/record/kind/store match merely because the date label differs from `/bin/date`.
5. Use `/bin/date` as a filter only when the request itself is day-scoped and the update's only relevant scope dimension is operating day, or when the update declares a live lockout/retry timestamp.
6. Apply the update only to the gate(s) it explicitly names. A role-delegation addendum does not override percent caps, status gates, reason-code enums, ownership, or post-state checks unless it says so verbatim.

## Output to the invoking BP

Return or record:

- matched update paths;
- scope dimensions that matched and any explicit contradictions;
- gate(s) overridden, delegated, blocked, or added;
- whether `/bin/date` was consulted and why;
- effective result: no match, override permits, override blocks now, or override changes a gate.

Every matched update that shaped the decision becomes an applied policy path for [refs](refs.md). A candidate that was read but did not match or shape the decision does not belong in `refs`.

## Outcomes

This BP does not submit a final outcome. The invoking domain BP maps the update result to `OUTCOME_OK`, `OUTCOME_DENIED_SECURITY`, `OUTCOME_NONE_UNSUPPORTED`, or `OUTCOME_NONE_CLARIFICATION`.

## Anti-patterns

- Treating a dated update as expired solely because its date label differs from `/bin/date`.
- Applying an addendum to gates it did not name.
- Scanning only the four cross-workflow folders when the invoking BP supplied a narrow topic folder such as `/docs/payments/`.
- Scanning the whole `/docs` root because the base policy is `/docs/<file>.md`.
- Citing a candidate update that was read but did not match or shape the decision.
- Letting this helper authorize a mutation. It only returns update semantics to the domain BP.

## Dependencies

> If any of these dependencies change, this BP file may have become stale and must be re-derived.

- `/bin/date` (`--help`) - trusted date/timestamp provider used for operating-day and lockout comparisons.
