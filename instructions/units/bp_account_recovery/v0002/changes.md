# bp_account_recovery v0002

- mode: `manual_refactor`
- created_by: `human`
- created_at: `2026-06-19T17:06:00+00:00`
- parent: `v0001`

## Rationale

Convert the new account-recovery BP from the obsolete "Refs to set in scratchpad" heading to the active Evidence ledger template. Domain gates, outcomes, dependencies, and refs semantics are unchanged; the local evidence roles are now explicit so shared refs can remain generic.

## Rollback

Retire this version to fall back to v0001 if the template-only rewrite weakens account-recovery evidence handling.

## Dependencies
- `workspace:/docs/security.md` — Customer-only account recovery rule, /bin/id account-match gate, and account-recovery incident pattern.
- `workspace:/run/actions/README.md` — Defines the account-recovery-<customer_id>.json control-file naming this BP re-reads for post-state confirmation.
- `bin_help:account-recovery.help.txt` — Tool signature send-email-link <customer_id> <destination_email> and the policy-not-enforced disclaimer; send-email-link is the only supported verb.
- `bin_help:id.help.txt` — /bin/id output drives the customer-actor and ownership gate.
- `sql_table:customer_accounts` — customer_id ownership link to /bin/id and customer_email private contact field.
