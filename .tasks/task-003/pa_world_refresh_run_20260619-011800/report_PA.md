# Process Architect report — world_refresh

- job_id: `pa-world-refresh-1781821086-0000-v0004`
- mode: `world_refresh` (queue priority: `blocking_refresh`)
- terminal_status: **`completed`**
- exit_code: `0`
- duration: 373s

## Inputs

- trigger task: `t01`
- trigger trial: `vm2-LytsXNjnYw2VdsQ498f45ZY7TcC`
- baseline_version: `v0004`

## Decision

- mode (from decision): `world_refresh`

### Changes (1)

**`bp_index`** (base `v0007`)

_Rationale_: A new mutating runtime tool (/bin/account-recovery) plus a new /docs/security.md customer-only account-recovery rule create a distinct domain that the process map did not route. Added a §1 routing row pointing at the new business_processes/account_recovery.md and a §9 cross-cutting note (customer-only; 'recovery' is authority bait). All other rows, principles, outcome tokens, and the mutation gate are unchanged.

### New units (1)

**`bp_account_recovery`**

_Rationale_: New mutating capability /bin/account-recovery (send-email-link <customer_id> <destination_email>) writes /run/actions/account-recovery-<customer_id>.json and is pinned by a new /docs/security.md rule making account recovery / email-change verification customer-only (link only to the account matching /bin/id). A mutating tool with its own gate, output file, and policy is a distinct atomic domain — separate from identity_and_auth (the general identity/ownership gate, which this BP applies via link) and from payments_3ds_recovery (payment recovery, not account recovery). The tool README states it 'does not enforce /docs/security.md', so a BP must.
- unchanged (15):
  - `bp_identity_and_auth`
  - `bp_privacy_and_disclosure`
  - `bp_refs`
  - `bp_submission_terminal`
  - `bp_fraud_risk_review`
  - `bp_policy_update_scan`
  - `bp_product_discovery`
  - `bp_basket_lifecycle`
  - `bp_checkout`
  - `bp_discount`
  - `bp_payments_3ds_recovery`
  - `bp_returns`
  - `bp_date_and_time`
  - `bp_background_decoys`
  - `bp_os_tooling_incidents`

### Notes for human

Single drift this refresh: a new mutating domain. New tool /bin/account-recovery (send-email-link <customer_id> <destination_email>) + /bin/README.md note + rewritten /run/actions/README.md (output file account-recovery-<customer_id>.json) + surgical /docs/security.md edit making account recovery / email-change verification customer-only and adding the recovery-link denial incident pattern. Owning-layer decision: domain_policy -> new narrow topic BP (bp_account_recovery), routed in bp_index; the general identity rule stays in identity_and_auth (linked, not duplicated). No drafts existed in processes/drafts (empty), so there were no ground/merge/prune decisions to make. relocations.json confirms the only added file is vault/bin/account-recovery and there are no renames/removals. Note: vault/bin/account-recovery is empty in the dump (binary/elided) — the BP is grounded on the tool --help, /bin/README.md, /run/actions/README.md, and /docs/security.md, per the contract to use bin-help as the tool-surface authority. Every world-changes.md row and every bin-help-diff.patch hunk is accounted for by these two units.

## Outcome

- num_turns: `32`
- total_cost_usd: `1.9190595000000001`
- duration_ms: `337327`
  - files_read: `23`
  - files_under_version_history_read: `0`
  - files_edited: `0`
  - files_written: `3`
  - bash_calls: `0`
  - deps_declared: `0`

## Created versions

- `bp_index` → `v0008`  (see `agent/instructions/units/bp_index/v0008/changes.md`, `agent/instructions/units/bp_index/v0008/diff.patch`)
- `bp_account_recovery` → `v0001`  (see `agent/instructions/units/bp_account_recovery/v0001/changes.md`, `agent/instructions/units/bp_account_recovery/v0001/diff.patch`)
- new world baseline: `v0005`

## Conflict resolution

- base was stale at apply: no
- conflict retries: 0
