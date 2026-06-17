# bp_payments_3ds_recovery v0003

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-05-21T11:40:33+00:00`
- parent: `v0002`

## Rationale

Trial graded FAIL with 'answer missing required reference /docs/policy-updates/3ds-retry-lockout-2024-07-17.md' on an OUTCOME_OK 3DS recovery. The customer / basket / payment / status-table gates all passed, and the Executor ran /bin/payments recover-3ds correctly, but it never swept the dated-update folders named by /docs/README.md ('Before applying an active decision policy, check under /docs for dated policy updates that name the same workflow, record, or operating day'). A matching update under /docs/policy-updates/ named the specific payment under review and imposed a retry lockout window — the Executor missed it because the previous BP only described the legacy /docs/payments/3ds.md gates and the /docs/checkout.md prerequisite, with no mandatory sweep across /docs/policy-updates/ etc. before the mutation. The new version adds a 'Policy-update sweep' step between the eligibility gates and the recover-3ds call: list each dated-update folder named in /docs/README.md, identify matching updates by payment id, basket id, customer id, 3DS / payment-recovery workflow keywords, or operating day (per the scope-dimension grammar already in [date_and_time]), read each match, apply its override (lockout windows compared against /bin/date, hard suspensions, altered caps), cite every matching update path in refs regardless of outcome. The sweep is gated on identity-matched flows only — the cross-boundary OUTCOME_DENIED_SECURITY branch still cites policy docs only. Inputs, Outcomes, Refs, Anti-patterns and Dependencies are updated to keep the rule consistent across the unit.

## Rollback

If the new Policy-update sweep mis-fires (e.g. grader rejects a dated update path that turned out not to match, or graders stop requiring update paths in refs), create a new version from v0002 content to restore the three-doc-only refs rule without the dated-update sweep.

## Dependencies
- `workspace:/docs/payments/3ds.md` — Authoritative 3DS recovery policy. Gate set, legacy status table, forbidden actions, and the prerequisite line naming /docs/security.md and /docs/checkout.md all come from this doc; if it changes the BP's Process and Anti-patterns become stale.
- `workspace:/docs/checkout.md` — Prerequisite policy that /docs/payments/3ds.md defers to. The BP requires reading and citing this doc on ownership-matched outcomes; if the live doc is renamed or removes the checkout prerequisites the three-doc refs rule needs re-derivation.
- `workspace:/docs/security.md` — Identity / cross-boundary rule named alongside /docs/checkout.md in the 3DS prerequisite line; the cross-boundary OUTCOME_DENIED_SECURITY refs branch and the policy-applied bundle both cite it directly.
- `workspace:/docs/README.md` — Defines the dated-update folder family (/docs/policy-updates/, /docs/current-updates/, /docs/ops-policy-notes/, /docs/catalogue-addenda/) and the rule that a matching update overrides the base policy. The new Policy-update sweep step is derived directly from this doc; if the folder list or the override rule moves the sweep must be re-derived.
- `bin_help:payments.help.txt` — Defines the /bin/payments tool signature; the BP names recover-3ds as the only subcommand. If the tool grows verbs or renames recover-3ds, Inputs / Process become stale.
