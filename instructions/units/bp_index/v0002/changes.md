# bp_index v0002

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-22T02:15:37+00:00`
- parent: `v0001`

## Rationale

The returns row in the 'When to read what' table claimed 'no dedicated decision policy' for returns — drift on /docs/README.md adds /docs/returns.md to the Active Decision Policies table, so that claim is now wrong. The Mutation gate section also enumerated /bin/checkout, /bin/discount, /bin/payments recover-3ds as the mutating tool list without /bin/payments approve-refund / refund; the cross-cutting principles did not call out that refund mutation splits by actor kind (employee approval vs owning-customer finalization). Refresh to (a) rewrite the returns row to point at the two refund workflows and the matching tool subcommands, (b) add a fourth cross-cutting principle covering the actor-kind split, and (c) extend the Mutation gate's tool list, role examples, and state-gate examples to cover the refund-approval and refund-finalization gates.

## Rollback

Create a new version from v0001 content if the new returns row over-triggers the BP (e.g. the Executor consults bp_returns for plain product / catalogue lookups because the request mentioned the word 'return' in passing) or if the actor-kind cross-cutting principle conflicts with a future role consolidation.
