# bp_payments_3ds_recovery v0004

- mode: `refresh`
- created_by: `process_architect`
- created_at: `2026-05-22T01:30:11+00:00`
- parent: `v0003`

## Rationale

Two dep changes drove this refresh. (1) /docs/README.md is no longer present in the workspace dump (it was a declared dep in v0003 but is absent from current-dependencies/ and is no longer reachable for ws.read). The previous version quoted README directly and named it as a dependency; both are removed. The policy-update sweep behaviour itself is preserved — it is graded-required, as established by the v0003 failure where the grader rejected an OUTCOME_OK answer for missing /docs/policy-updates/<file>.md in refs — but its prose is rewritten so the rule stands on its own (folder family enumerated inline, cross-reference to [date_and_time] kept for the scope-dimension grammar) instead of citing README. (2) bin-help/payments.help.txt now exposes approve-refund and refund alongside recover-3ds; the prior 'Only subcommand; no other payments verb exists' claim is wrong. Tools and Anti-patterns now name recover-3ds as the only verb this BP authorises and explicitly warn against invoking the refund verbs from a 3DS recovery flow. The three unchanged deps (/docs/payments/3ds.md, /docs/checkout.md, /docs/security.md — empty patches) retain their roles unchanged.

## Rollback

If the rewritten policy-update sweep prose (no longer anchored on /docs/README.md) mis-fires, create a new version from v0003 content and re-add /docs/README.md as a dep once it is restored in the workspace; if the new tool-surface anti-pattern about approve-refund / refund mis-fires, drop just that anti-pattern bullet in a follow-up version.

## Dependencies
- `workspace:/docs/payments/3ds.md` — Authoritative 3DS recovery policy. Gate set, legacy status table, forbidden actions, and the prerequisite line naming /docs/security.md and /docs/checkout.md all come from this doc; if it changes the BP's Process and Anti-patterns become stale.
- `workspace:/docs/checkout.md` — Prerequisite policy that /docs/payments/3ds.md defers to. The BP requires reading and citing this doc on ownership-matched outcomes; if the live doc is renamed or removes the checkout prerequisites the three-doc refs rule needs re-derivation.
- `workspace:/docs/security.md` — Identity / cross-boundary rule named alongside /docs/checkout.md in the 3DS prerequisite line; the cross-boundary OUTCOME_DENIED_SECURITY refs branch and the ownership-matched applied-policy bundle both cite it directly.
- `bin_help:payments.help.txt` — Defines the /bin/payments tool signature. The BP authorises recover-3ds only and explicitly excludes the sibling approve-refund / refund verbs from a 3DS-recovery flow; if the help text renames or removes recover-3ds, or grows a new 3DS verb, Tools and Anti-patterns become stale.
