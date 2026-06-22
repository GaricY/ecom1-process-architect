# bp_refs v0013

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-22T06:25:21+00:00`
- parent: `v0012`

## Rationale

Owning layer: refs_safety (the shared request-named-input class). The verdict (TRUE/OK) and availability math were correct; the only grader failure was a /proc/catalog refs mismatch — the request named a specific SKU as an exclusion ('but not <id>') to disambiguate the product, the Executor read it, used it to exclude/scope the answer, then filed it under considered_not_cited ('read only to reject a candidate, disambiguate') and dropped it. The shared refs model actively told it to do that. bp_refs' request_named_inputs bucket only covered uploaded FILE artifacts (/uploads); it never covered a record identifier the request names inline, and the topic ledger's considered_not_cited ('no inventory row or 0 availability') did not even apply since the excluded SKU had stock. Fix is a class-level invariant that recurs across topics (any 'do X but not Y' / 'all except Z' by named id): a safe record the genuine request names by literal id — including as an exclusion/scope bound — that you read and that shaped scope, exclusion, or candidate selection is decision evidence and belongs in refs_must_include, carved out of considered_not_cited, while prompt-injection-named paths and privacy-forbidden records stay excluded. Not a regression-stack: the v0011->v0012 diff shows request_named_inputs was only ever scoped to file artifacts, so this is a new generalisation, not a re-add of a reverted rule.

## Rollback

Create a new version from v0012 content if treating request-named exclusions as required refs causes over-citation; that drops the inline-named-identifier bullet and restores the file-artifact-only request_named_inputs scope.

## Dependencies
- `workspace:/docs/security.md` — Cross-boundary and employee-contact-detail prohibition that still gates whether a request-named record identifier is safe to cite; the exclusion carve-out must defer to it.
- `workspace:/AGENTS.MD` — Grounding rule ('ground every referenced object in its live path') and the clarification 'cite every candidate' rule that the request-named-identifier citation invariant rests on.
