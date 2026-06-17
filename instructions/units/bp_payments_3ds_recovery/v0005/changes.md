# bp_payments_3ds_recovery v0005

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-05-22T02:58:29+00:00`
- parent: `v0004`

## Rationale

Trial graded FAIL with 'answer missing required reference /docs/payments/3ds-retry-window-2024-07-17.md' on an OUTCOME_OK 3DS recovery. The Executor correctly ran identity, status-table, and attempt-count gates, then performed the policy-update sweep exactly as the v0004 BP described — listing /docs/policy-updates/, /docs/current-updates/, /docs/ops-policy-notes/, /docs/catalogue-addenda/. All four returned 'not found'. The Executor concluded no update applied and called /bin/payments recover-3ds. But the actual override was a date-stamped sibling to the topic doc itself, living in /docs/payments/ next to /docs/payments/3ds.md. /docs/README.md grounds the rule on 'check under /docs for dated policy updates' — scoped to /docs, not to a fixed four-folder list — and v0004 narrowed the rule to a fixed list that does not cover topic-folder siblings. The new version splits the sweep into Class A (the topic doc's own folder /docs/payments/) and Class B (the four cross-workflow folders, retained), requires listing both in the same snippet, treats every entry in /docs/payments/ other than 3ds.md as a candidate update, and adds a refs / anti-pattern bullet covering /docs/payments/<file>.md as the matching-update path family. Outcomes, Refs, Anti-patterns and Dependencies are updated to keep the rule consistent across the unit; /docs/README.md is re-added as a declared dependency since the sweep-scope rule is derived directly from its 'check under /docs' wording (it is present in the current vault dump).

## Rollback

If the new Class-A sweep over /docs/payments/ mis-fires (e.g. grader rejects a topic-folder sibling that turned out not to match, or treats the topic-folder sibling rule as out-of-scope for this BP), create a new version from v0004 content to restore the four-folder-only sweep.

## Dependencies
- `workspace:/docs/payments/3ds.md` — Authoritative 3DS recovery policy. Gate set, legacy status table, forbidden actions, and the prerequisite line naming /docs/security.md and /docs/checkout.md all come from this doc. Also the doc whose own folder (/docs/payments/) is now an explicit Class A sweep target for date-stamped sibling updates; if this doc moves out of /docs/payments/, the Class A sweep target must move with it.
- `workspace:/docs/checkout.md` — Prerequisite policy that /docs/payments/3ds.md defers to. The BP requires reading and citing this doc on ownership-matched outcomes; if the live doc renames or removes the checkout prerequisites the three-doc refs rule needs re-derivation.
- `workspace:/docs/security.md` — Identity / cross-boundary rule named alongside /docs/checkout.md in the 3DS prerequisite line. Both the cross-boundary OUTCOME_DENIED_SECURITY refs branch and the ownership-matched applied-policy bundle cite it directly.
- `bin_help:payments.help.txt` — Defines the /bin/payments tool signature. The BP authorises recover-3ds only and explicitly excludes the sibling approve-refund / refund verbs from a 3DS-recovery flow; if the help text renames or removes recover-3ds, or grows a new 3DS verb, Tools and Anti-patterns become stale.
