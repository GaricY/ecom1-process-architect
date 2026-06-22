# bp_availability_and_inventory v0003

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-22T10:43:08+00:00`
- parent: `v0002`

## Rationale

Owning layer: terminal_protocol leak into the topic BP. This is the topic BP the Executor selected; its reply-shaping step told it directly to 'use the TRUE(1)/FALSE(0) token' for yes/no — the proximate instruction that produced the wrong literal instead of live `/AGENTS.MD`'s `ja`/`nein`. The conflicting v0002 fixed an unrelated topic_evidence failure (requiring a catalogue record in refs for every request-named SKU) and merely renumbered the stale reply-shaping rule from step 6 to step 7, leaving the `TRUE(1)/FALSE(0)` literal intact — so my concern is not subsumed; I extend v0002. I keep all of v0002's catalogue-citation cohort rules and only change step 7 so reply shaping records the boolean verdict / integer and defers the final token to bp_submission_terminal (which emits the live `/AGENTS.MD` yes/no/count token), plus one anti-pattern against hard-coding the literal. No new literal is introduced, so the rule cannot drift again when the live token changes; this is consistent with bp_submission_terminal's anti-pattern forbidding topic BPs from restating the token. Dependency set is unchanged from v0002.

## Rollback

Create a new version from v0002 content (restores 'for yes/no use the TRUE(1)/FALSE(0) token' in step 7) if deferring the token to submission_terminal proves insufficient.

## Dependencies
- `workspace:/docs/availability-checks.md` — Same-day availability formula (max(on_hand-reserved,0)), incoming/due-within rules, read-only constraint, and the inventory-export schema this BP applies.
- `bin_help:availability.help.txt` — The /bin/availability tool and its max(on_hand-reserved,0) / missing-SKU-0 same-day contract.
- `sql_table:locations` — Branch record and inventory rows (on_hand, reserved, incoming.arrival_in_days) used to compute availability.
- `sql_table:catalog` — Per-SKU catalogue record (/proc/catalog/<brand>/<sku>.json) used to resolve requested products, cite request-named SKUs, and build family exports.
