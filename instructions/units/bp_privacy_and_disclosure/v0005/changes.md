# bp_privacy_and_disclosure v0005

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-18T23:08:58+00:00`
- parent: `v0004`
- no_semantic_change: revalidated against the new dependency hashes without text edits

## Rationale

world_refresh: PA reviewed this BP and recorded it as unchanged; orchestrator re-stamped drifted dependency hashes (/docs/security.md) so the unit re-matches the refreshed world instead of falling back stale. No content change.

## Rollback

rollback to v0004 (content identical; only dependency hashes were re-stamped)

## Dependencies
- `workspace:/docs/security.md` — Personal-information and cross-boundary disclosure rule.
- `bin_help:id.help.txt` — Actor output shape for ownership/disclosure branching.
- `sql_table:customer_accounts` — Customer contact/profile fields (customer_email, home_city, home_latitude, home_longitude) that are private by default.
- `sql_table:employee_accounts` — Employee roster, assigned store (store_id), and contact fields (employee_email, job_title).
- `workspace:/proc/customers/README.md` — Customer email and coarse home-area coordinate semantics.
