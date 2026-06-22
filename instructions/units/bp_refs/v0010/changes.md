# bp_refs v0010

- mode: `refresh`
- created_by: `process_architect`
- created_at: `2026-05-30T18:09:18+00:00`
- parent: `v0009`

## Rationale

Unit-dep drift in /docs/attachments.md renamed the upload root from /uploads to /storage; the BP cites the old name in three prose places (class-1 grounding example, Inputs example, What-not-to-include exclusion clause) and in the Dependencies gloss, so all four references update to /storage to match the live policy. World-dep drift in /AGENTS.MD renamed employee records from /proc/staff to /proc/employees; the identity-scoped record families list quoted the old path and is updated to /proc/employees so the cross-boundary rule still names a live path. No change to citation/ownership logic or to the dep contract.

## Rollback

Revert content.md to v0009 wording (/uploads in the three prose mentions plus the dependency gloss; /proc/staff in the identity-scoped families list); the dependency set is unchanged.

## Dependencies
- `workspace:/docs/security.md` — Cross-boundary rule and personal-information disclosure boundary.
- `workspace:/docs/attachments.md` — Defines /storage as the request-named input-artifact root for class-1 grounding.
- `bin_help:id.help.txt` — Actor output shape for customer/employee/guest branching.
