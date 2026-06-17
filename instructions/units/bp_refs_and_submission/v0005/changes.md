# bp_refs_and_submission v0005

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-22T02:15:37+00:00`
- parent: `v0004`

## Rationale

Two coupled drifts. First, the topic-doc routing table's returns row read 'the active returns policy under /docs/... (resolve via ws.tree(/docs))' — a placeholder pending a stable doc path. /docs/README.md drift adds /docs/returns.md as an Active Decision Policy, so the row should name it directly (plus the explicit triggers the Executor sees: ret_* id, refund verbs, refund_pending status). Second, the /bin/payments binary now hosts three subcommands routing to two distinct topic docs (recover-3ds -> /docs/payments/3ds.md, approve-refund / refund -> /docs/returns.md); without a disambiguation note the Executor will route a refund request to /docs/payments/3ds.md because the binary is the same. Adds a 'one binary, three subcommands, two topic docs' note, an anti-pattern for the same trap, mentions refund_manager in the own-record capability-gap example list, and extends the employee-actor exception examples to mention refund approval. The 'Dependencies' prose section still notes /docs/README.md as a tracked input even though it cannot appear in the machine-readable dependency list (world file).

## Rollback

Create a new version from v0004 content if the new routing-table row over-routes (e.g. a basket-lifecycle question that uses the word 'return' as in 'return to the store' gets routed to /docs/returns.md) or if the refund-binary disambiguation conflicts with a future /bin/payments verb that does not cleanly belong to either topic doc.

## Dependencies
- `workspace:/docs/security.md` — Cross-boundary rule, 'no release of personal information across the boundaries' clause, Identity Audit Phrases denial templates — cited throughout the customer-actor and employee-actor branches.
- `bin_help:id.help.txt` — Defines the shape of /bin/id output (user, roles) that the actor-type branching (cust_* / emp_* / guest) and the pre-submission checklist key off.
