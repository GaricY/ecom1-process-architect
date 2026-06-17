# bp_refs v0005

- mode: `failure_fix`
- created_by: `human`
- created_at: `2026-05-28T19:48:25+00:00`
- parent: `v0004`

## Rationale

Failure-driven fix for run 20260528-214615 (t52 + t53, both 0%). The only score_detail was "answer missing required reference '/uploads/receipt_ocr_*.txt'": the agent read the OCR receipt as the sole source of the old prices/SKUs/quantities but never cited it. bp_refs had no category for request-named input artifacts — its closed-world model enumerated only /proc record families and /docs policies, and /uploads sits outside all of them. Adds a 'Grounding principle' section (path-agnostic: bind to the artifact's role, not the /uploads folder name, since a future run may call it /incoming etc.), a 'What to include' bullet, an Inputs line, an input-artifact checklist step (renumbering 4-7 -> 5-8), and an anti-pattern. Also restores the original live-vs-mirror rationale to the vault exclusion (compressed to 'Local vault/... paths.' during the bp_refs_and_submission -> bp_refs decomposition, commit 56d6dd6) so /uploads is unambiguously citeable. Actor/ownership branches, public-record sweep, discovery set-equality, topic-doc routing, and the dependency contract are unchanged. Analysis: .tasks/task-024/analysis.md + bp_refs_review.md.

## Rollback

Revert to v0004 by creating a new version from v0004 content if the input-artifact rule causes over-citing (e.g. agents citing every file in an input folder) that regresses precision-capped scoring. Narrow rollback: drop only the 'Request-named input artifacts' What-to-include bullet + grounding-principle class 1, keeping the vault-exclusion rewording.

## Dependencies
- `workspace:/docs/security.md` — Authority for cross-boundary and personal-information citation boundaries.
- `bin_help:id.help.txt` — Actor output shape used for customer/employee/guest citation branches.
- `sql_table:shopping_baskets` — Basket ownership, store pointer, status, and canonical record_path for basket refs.
- `sql_table:payment_transactions` — Payment ownership, basket/store pointers, status, and canonical record_path for payment refs.
- `sql_table:return_requests` — Return ownership, basket/payment pointers, status, and canonical record_path for return refs.
- `sql_table:customer_accounts` — Customer identity and contact fields that are private by default.
- `sql_table:employee_accounts` — Employee roster/contact fields and assigned-store scope determine private vs operational refs.
- `sql_table:stores` — Public store record_path and location fields are required public-record refs.
- `sql_table:product_variants` — Public catalogue record_path and SKU fields are required public-record refs.
