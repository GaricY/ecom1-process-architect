# Process Architect report — failure_fix

- job_id: `pa-failure-fix-1781807180-0004`
- mode: `failure_fix` (queue priority: `failure_fix`)
- terminal_status: **`completed`**
- exit_code: `0`
- duration: 328s

## Inputs

- trigger task: `t52`
- trigger trial: `vm2-LytL1adto1bNwcu65BDpDPRGYpT`
- score at trigger: 0.0%
- answer_outcome: `OUTCOME_OK`
- failed task dir: `0006-t52-vm2-LytL1adto1bNwcu65BDpDPRGYpT`
- selected base versions:
  - `bp_background_decoys` → `v0003`
  - `bp_basket_lifecycle` → `v0005`
  - `bp_checkout` → `v0005`
  - `bp_date_and_time` → `v0004`
  - `bp_discount` → `v0011`
  - `bp_fraud_risk_review` → `v0007`
  - `bp_identity_and_auth` → `v0005`
  - `bp_index` → `v0006`
  - `bp_os_tooling_incidents` → `v0003`
  - `bp_payments_3ds_recovery` → `v0010`
  - `bp_policy_update_scan` → `v0004`
  - `bp_privacy_and_disclosure` → `v0004`
  - `bp_product_discovery` → `v0018`
  - `bp_refs` → `v0008`
  - `bp_returns` → `v0006`
  - `bp_submission_terminal` → `v0006`
  - `executor_core` → `v0014`

## Decision

- mode (from decision): `failure_fix`

### Changes (1)

**`bp_refs`** (base `v0008`)

_Rationale_: Owning layer: refs_safety (request-named-input class is bp_refs-owned per the layer map; the symptom surfaced in product_discovery's refs build, but that is the first-symptom unit, not the owner). The task pointed at an input file ("Look at the old receipt in /uploads/"); the Executor read /uploads/receipt_ocr_EDpwT7M9.txt, derived the old-total side of the comparison from it, but cited only the downstream catalogue records it compared against, so the grader flagged the missing required reference. bp_refs already carried the request-named-input rule, but it was bypassed structurally: the final-projection and checklist step 2 subordinate request-input classification to the topic BP ledger, and product_discovery's ledger has no request-input bucket, so the unconditional citation never fired. Fix narrows on the existing rule rather than adding a new safeguard: the request_named_inputs category is marked a shared invariant owned here (cite the input even when refs_must_include lists only the downstream records), and checklist step 5 is reworded into a hard topic-BP-independent backstop that fires even when the topic ledger never classified an input. The existing anti-pattern already describes this exact failure, so no new prose was added. Not a regressing PA rule: v0008 is a human Evidence-ledger refactor.

_Deps_: `workspace:/docs/security.md`, `bin_help:id.help.txt`, `sql_table:shopping_baskets`, `sql_table:payment_transactions`, `sql_table:return_requests`, `sql_table:customer_accounts`, `sql_table:employee_accounts`, `sql_table:stores`, `sql_table:product_variants`, `workspace:/proc/README.md`

## Outcome

- num_turns: `20`
- total_cost_usd: `1.6513624999999998`
- duration_ms: `295206`
  - files_read: `15`
  - files_under_version_history_read: `3`
  - files_edited: `0`
  - files_written: `2`
  - bash_calls: `0`
  - deps_declared: `10`

## Created versions

- `bp_refs` → `v0009`  (see `agent/instructions/units/bp_refs/v0009/changes.md`, `agent/instructions/units/bp_refs/v0009/diff.patch`)

## Conflict resolution

- base was stale at apply: no
- conflict retries: 0
