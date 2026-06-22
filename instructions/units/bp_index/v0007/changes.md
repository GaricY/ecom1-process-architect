# bp_index v0007

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-30T09:37:50+00:00`
- parent: `v0006`

## Rationale

Routing map drifted on every axis: returns now route to /bin/refund approve|close (not /bin/payments); a new availability domain (/docs/availability-checks.md) and dispatch domain (/docs/dispatch.md) need rows; checkout now also covers customer-only basket item edits; the os/tooling-incidents route is repurposed to a tooling-outage / unsupported-system gate (its grounding doc and /bin/claude,/bin/codex were removed); the SQL cluster is down so a cross-cutting 'read /proc JSON via /bin/jq|cat' principle and the new TRUE(1)/FALSE(0) yes/no token reference must be reflected; proc family and decoy references are renamed/swapped.

## Rollback

Restore bp_index content.md to v0006 (returns->/bin/payments, no availability/dispatch rows, old os_tooling row, SQL-projection product_discovery row, <YES>/<NO> token reference).
