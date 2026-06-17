# bp_index v0006

- mode: `failure_fix`
- created_by: `human`
- created_at: `2026-05-28T23:18:30+00:00`
- parent: `v0005`

## Rationale

De-specify the mutation-tool list out of executor_core (which world_refresh is forbidden to touch) into a world_refresh-maintainable BP unit. Adds a `Mutating` column to the section-1 table naming, per BP, the `/bin/*` tool(s) that BP owns; rewires section-4 to reference that column instead of re-listing the tools. Companion to executor_core v0013. Motivation: executor_core's `## Mutation preflight` hard-coded only `/bin/checkout`,`/bin/discount`,`/bin/payments recover-3ds` and had already gone stale vs this index's section-4, which already listed five mutators (added `approve-refund`,`refund`). Making section-1 the single canonical home prevents that drift. Dependency contract unchanged (prose-only).

## Rollback

Revert to v0005 if the column proves noisy or if section-4 readers need the inline list back; the tools are also enumerated per-BP (checkout/discount/payments_3ds_recovery/returns) so no information is lost.
