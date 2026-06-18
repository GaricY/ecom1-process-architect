# Process Architect report — failure_fix

- job_id: `pa-failure-fix-1781743897-0004`
- mode: `failure_fix` (queue priority: `failure_fix`)
- terminal_status: **`completed`**
- exit_code: `0`
- duration: 332s

## Inputs

- trigger task: `t51`
- trigger trial: `vm2-LyqwQdGCxK8ttvDXKk5w9t58m4W`
- score at trigger: 0.0%
- answer_outcome: `OUTCOME_OK`
- failed task dir: `0051-t51-vm2-LyqwQdGCxK8ttvDXKk5w9t58m4W`
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

**`bp_product_discovery`** (base `v0018`)

_Rationale_: The trial scored 0% with the verdict 'answer missing required reference <input path>': the Executor compared an old uploaded receipt against today's catalogue prices, computed the right answer, but cited only the four /proc/catalog/<sku>.json records it compared against and dropped the /uploads/ receipt that supplied the 'old' baseline. The Executor anchored on product_discovery as its primary BP. refs.md does carry a general request_named_inputs rule, but product_discovery's typed Evidence ledger (added in the v0018 refactor) enumerates refs_must_include for stores/products/docs only and has no placement for a handed-in input artifact. That incomplete-but-authoritative topic ledger overrode the general rule. This edit adds to product_discovery a 'Comparison against a handed-in input document' task shape, a request_named_inputs ledger bucket, a refs_must_include line, an Inputs entry, and a matching anti-pattern, all requiring the request-named input artifact's absolute live path in refs when the answer's baseline/old/claimed facts came from it. Generalises to any receipt/OCR/invoice/report/attachment comparison, not this trial's specific upload.

_Deps_: `bin_help:date.help.txt`, `bin_help:id.help.txt`, `sql_table:product_variants`, `sql_table:product_variant_properties`, `sql_table:product_families`, `sql_table:product_kinds`, `sql_table:store_inventory`, `sql_table:stores`, `workspace:/proc/stores/README.md`

## Outcome

- num_turns: `26`
- total_cost_usd: `1.6748815000000004`
- duration_ms: `345261`
  - files_read: `13`
  - files_under_version_history_read: `5`
  - files_edited: `1`
  - files_written: `2`
  - bash_calls: `1`
  - deps_declared: `9`

## Created versions

- `bp_product_discovery` → `v0019`  (see `agent/instructions/units/bp_product_discovery/v0019/changes.md`, `agent/instructions/units/bp_product_discovery/v0019/diff.patch`)

## Conflict resolution

- base was stale at apply: no
- conflict retries: 0
