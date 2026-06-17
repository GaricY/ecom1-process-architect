# bp_payments_3ds_recovery v0002

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-05-21T09:39:18+00:00`
- parent: `v0001`

## Rationale

Trial graded FAIL with 'answer missing required reference /docs/checkout.md' on an OUTCOME_OK 3DS recovery. The live policy /docs/payments/3ds.md opens with 'Before recovering 3DS, read and apply /docs/security.md and /docs/checkout.md', so /docs/checkout.md is a prerequisite policy applied during every ownership-matched 3DS recovery decision. The previous BP only required /docs/security.md and /docs/payments/3ds.md in refs, so a correct executor still dropped /docs/checkout.md. The new version names the three-doc applied-policy bundle explicitly, requires reading /docs/checkout.md during eligibility evaluation, lists it as an Input and Dependency, and adds a refs anti-pattern. The cross-boundary OUTCOME_DENIED_SECURITY case is kept policy-docs-only (security.md + 3ds.md) because checkout policy is not applied when identity blocks the flow before eligibility is checked.

## Rollback

If the new refs rule mis-fires (e.g. grader stops accepting /docs/checkout.md in cross-boundary cases), create a new version from v0001 content to restore the two-doc refs bundle.

## Dependencies
- `workspace:/docs/payments/3ds.md` — Authoritative 3DS recovery policy. The opening sentence ('Before recovering 3DS, read and apply /docs/security.md and /docs/checkout.md') is the basis for the new three-doc applied-policy rule. If this doc drops the checkout prerequisite, the new refs rule must be re-derived.
- `workspace:/docs/checkout.md` — Prerequisite policy that /docs/payments/3ds.md defers to. The new version requires reading and citing this doc on ownership-matched outcomes; if the live doc is renamed or removed the rule needs to be re-derived.
- `workspace:/docs/security.md` — Identity / cross-boundary rule named alongside /docs/checkout.md in the 3DS prerequisite line; the cross-boundary refs branch in this BP cites it directly.
- `bin_help:payments.help.txt` — Defines the /bin/payments tool signature; this BP names recover-3ds as the only subcommand. If the tool grows verbs or renames recover-3ds, the BP's Inputs / Process sections become stale.
