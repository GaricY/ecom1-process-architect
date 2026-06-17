# bp_returns v0002

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-22T02:15:37+00:00`
- parent: `v0001`

## Rationale

World drift in /AGENTS.MD and /docs/README.md acknowledges a new returns decision policy (/docs/returns.md) and refund mutators on /bin/payments (approve-refund, refund). bp_returns v0001 was authored when neither existed; it asserted 'No dedicated decision policy exists under /docs/ for returns' and 'no /bin/returns tool' and routed every return mutation to OUTCOME_NONE_UNSUPPORTED. Both claims are now wrong. Rewrite the BP to (a) carry the two refund workflows verbatim from /docs/returns.md (refund_manager approval gate, owning-customer finalization gate), (b) name the two /bin/payments subcommands as the mutators, (c) keep the information-lookup path and the no-replacement-tool path, (d) update Refs guidance to add /docs/returns.md and /docs/security.md as the applied-policy bundle whenever the refund flow was evaluated, and (e) refresh anti-patterns (the old 'invent /docs/returns.md is wrong' anti-pattern is now backwards, the new traps are wrong-role / wrong-status / hand-editing files / employee-finalizing-on-behalf).

## Rollback

Create a new version from v0001 content if the rewrite over-blocks legitimate refund flows (e.g. denies a refund_manager approval that was correctly described) or if it under-blocks a wrong-actor finalization; the v0001 'all return mutations unsupported' rule was conservative.

## Dependencies
- `workspace:/docs/returns.md` — Full gate set for both refund workflow steps (approval, finalization), the refund_manager role enum, the status enum (approved -> refund_pending -> finalized), and the prohibition on editing return files by hand. The BP quotes its gate text verbatim.
- `workspace:/docs/security.md` — /docs/returns.md names it as a prerequisite ('read and apply /docs/security.md') for both refund workflow steps; the BP cites it in the applied-policy bundle on every authorised outcome and in the cross-boundary denial branch.
- `bin_help:payments.help.txt` — Tool signature for approve-refund <return_id> and refund <return_id>. The Process and Tools sections quote the subcommand semantics and the help text guarantees both verbs (and only these refund verbs) currently exist.
