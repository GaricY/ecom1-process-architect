# bp_checkout v0008

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-22T06:46:57+00:00`
- parent: `v0007`

## Rationale

Owning layer: domain_policy (bp_checkout). The Executor was asked to check out a basket whose only line was a digitally-fulfilled SKU. It applied the checkout same-day-availability gate to that line, read /bin/availability = 0, and answered OUTCOME_NONE_UNSUPPORTED; the basket was actually eligible (expected OUTCOME_OK). Root cause: the v0007 world_refresh copied the availability gate from /docs/checkout.md but dropped that doc's carve-out ('Digital products are fulfilled by access/download', i.e. never stocked). This narrows the gate rather than stacking a new safeguard: the same-day availability gate now applies to physically-fulfilled lines only; the Executor must read each line's /proc/catalog fulfillment_type and exempt digital lines (a 0 from /bin/availability for a digital SKU is expected, not a stock failure), so a digital-only basket checks out without a store-inventory query. Outcomes, the evidence ledger, and anti-patterns are aligned to the physical-only scope.

## Rollback

Create a new version from v0007 content to drop the digital-fulfilment carve-out and restore the availability gate over every basket line if the physical/digital split proves wrong.

## Dependencies
- `workspace:/docs/checkout.md` — Item-edit rules, checkout gate set, the same-day availability formula, the digital-fulfilment carve-out ('Digital products are fulfilled by access/download'), and the customer-only scope.
- `workspace:/docs/security.md` — Identity/ownership gate applied via identity_and_auth before the line gate.
- `bin_help:checkout.help.txt` — /bin/checkout tool signature.
- `bin_help:availability.help.txt` — Same-day availability tool used for the physically-fulfilled per-line checkout gate.
- `sql_table:carts` — Ownership, status, store pointer, and lines.
- `sql_table:locations` — Store inventory (on_hand/reserved) for the availability gate on physical lines.
- `sql_table:catalog` — SKU resolution for item edits and the fulfillment_type that classifies each checkout line as physical (gate applies) or digital (exempt).
