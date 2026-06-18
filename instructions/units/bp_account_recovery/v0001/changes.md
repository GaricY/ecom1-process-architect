# bp_account_recovery v0001

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-18T23:08:58+00:00`

## Rationale

The new mutating tool /bin/account-recovery send-email-link, the new /docs/security.md rule making account recovery / email-change verification a customer-only action gated on the /bin/id account match, the new account-recovery incident pattern, and the /run/actions/README.md control-file naming together ground a new atomic domain. It is a distinct customer-only workflow (its own tool, gates, post-state record, and unsupported cases), not an extension of any existing topic BP; identity/ownership and privacy stay delegated to their owning BPs via cross-links.

## Rollback

Delete business_processes/account_recovery.md from the registry and revert bp_index to v0007; no other unit references it.

## Dependencies
- `workspace:/docs/security.md` — sole authority making account recovery / email-change verification a customer-only action and gating the link on the /bin/id account match; also the source of the account-recovery incident pattern
- `workspace:/run/actions/README.md` — defines the account-recovery-<customer_id>.json control-file naming this BP re-reads for post-state confirmation
- `bin_help:account-recovery.help.txt` — tool signature send-email-link <customer_id> <destination_email> and the policy-not-enforced disclaimer; send-email-link is the only supported verb
- `bin_help:id.help.txt` — /bin/id output drives the customer-actor and ownership gate (customer_id == /bin/id user)
- `sql_table:customer_accounts` — customer_id is the ownership link to /bin/id and customer_email is the private contact field the BP must not leak
