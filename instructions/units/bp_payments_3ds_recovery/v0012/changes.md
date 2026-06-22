# bp_payments_3ds_recovery v0012

- mode: `refresh`
- created_by: `process_architect`
- created_at: `2026-05-30T18:07:18+00:00`
- parent: `v0011`

## Rationale

/docs/payments/3ds.md raised the per-session attempt cap from 2 to 3. The BP cited the cap in two places (step 4 parenthetical and the Dependencies `why`); both now read `3 attempts` / `3-attempt cap`. The verbatim `/docs/payments/3ds.md` status-table quote, the retry_after/3ds-status1 semantics, the recover-3ds invocation, and `attempts < max_attempts` / `attempts >= max_attempts` formulations are unchanged — the policy still gates on the doc-defined `max_attempts`, only the documented ceiling moved. The unrelated world_dep drift (`/proc/staff` → `/proc/employees` in `world_base/AGENTS.MD`) does not touch this BP — it never references staff/employee paths.

## Rollback

Revert to v0011 (bp_admin rollback bp_payments_3ds_recovery --from v0011) to restore the 2-attempt wording if `/docs/payments/3ds.md` is rolled back.

## Dependencies
- `workspace:/docs/payments/3ds.md` — Full gate set, the customer-identity gate, retry_after/3ds-status1 semantics, the 3-attempt cap, the recover-3ds invocation, and the security.md+checkout.md prerequisite line.
- `workspace:/docs/checkout.md` — Prerequisite policy that 3DS recovery defers to (named in the 3ds.md prerequisite line and required in OK / NONE_UNSUPPORTED refs).
- `workspace:/docs/security.md` — Identity / cross-boundary rule named in the 3DS prerequisite line; governs the customer-actor match and the DENIED_SECURITY refs shape.
- `bin_help:payments.help.txt` — Tool signature; this BP authorises `recover-3ds` only (refund subcommands have moved off this binary).
- `bin_help:date.help.txt` — Trusted clock for `retry_after` / lockout comparison.
