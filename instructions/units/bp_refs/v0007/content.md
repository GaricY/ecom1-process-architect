# Refs

## When this process applies

Read this process whenever a `refs` list is being assembled or checked for an answer, denial, clarification, unsupported result, or final `submit_and_exit`. This file owns citation safety and evidence completeness. Use [submission_terminal](submission_terminal.md) only after `refs` is ready.

## Grounding principle

A `ref` is any object the answer is **derived from or grounded in** — cite it by its absolute **live** path (`/AGENTS.MD`: "provide full path to the object"). Three classes, ordered by how easily they are missed:

1. **Request-named input artifacts** — any file or document the task instruction itself points you to and that you read to build the answer. Bind to the role ("the task told me to read this, and I used it"), **not** to a folder name: it may live under `/uploads/`, `/incoming/`, `/inbox/`, an attachment path, or a pasted document saved into the workspace. Same boundaries as any record: an artifact tied to the current request/actor is citeable; one exposing another customer's identity-scoped data follows the cross-boundary/privacy branch below.
2. **Applied policy docs** — every `/docs/...` policy whose rule actually shaped the decision.
3. **Records read or identified** — identity-scoped and public `/proc/...` records, per the actor/ownership branches below.

The branches, sweeps, and tables below **refine** classes 2–3; they are not the whole universe. If the answer leans on an object that fits none of the named families, this principle still governs — cite it by its live path. Precision governs equally: cite the specific named source you used, not every neighbouring file. Over-citing unrelated objects is as harmful as omitting a required one.

## Inputs

- `/docs/security.md` - the cross-boundary and personal-information rule.
- `/bin/id` / `ws.id()` - actor type and roles.
- Request-named input artifacts - any file/document the task instruction points you to and reads to build the answer (e.g. an uploaded receipt under `/uploads/`); see the grounding principle.
- SQL `record_path` columns - canonical cite paths for rows that are actually safe to cite (every table exposes `record_path`; the old `path` column name no longer exists).
- Topic BPs - decide which policy docs and records were actually applied.

## Actor and ownership branches

Always branch on both actor type and ownership before deciding refs:

- Customer actor (`cust_*`) on a foreign identity-scoped record: cross-boundary denial. Cite policy docs only, plus any request-named public records. Do not cite the foreign basket/payment/return/customer record.
- Customer actor on their own record but lacking a capability: capability-gap denial on an owned record. Cite policy docs plus the owned action target and any required public records.
- Employee actor on a requested employee-shaped action: cite policy docs plus the action target even on role denial or unsupported state. The target is the work item the employee was asked to handle.
- Guest actor: no customer-owned record can pass ownership. Treat identity-scoped record requests as cross-boundary unless the task is purely public catalogue/store discovery.

Identity-scoped record families include baskets, payments, returns, customers (SQL tables `shopping_baskets`, `payment_transactions`, `return_requests`, `customer_accounts`), and employee contact/profile details (`employee_accounts`). Public records include catalogue products (`product_variants`) and stores.

## Topic policy docs

Include every active policy doc actually applied. Cross-boundary denials still include the topic doc because the denial is on that requested topic:

| Request shape | Topic doc |
| --- | --- |
| Checkout / place order / `/bin/checkout` | `/docs/checkout.md` |
| Discount / make-good / `/bin/discount` | `/docs/discounts.md` |
| 3DS recovery / `pay_*` stuck / `requires_3ds_action` | `/docs/payments/3ds.md` |
| Return / refund / `ret_*` / refund status tokens | `/docs/returns.md` |

Tie-breakers:

- A 3DS recovery request may say "checkout"; a `pay_*` id or 3DS wording makes `/docs/payments/3ds.md` the topic doc.
- `/bin/payments recover-3ds` is governed by `/docs/payments/3ds.md`; `/bin/payments approve-refund` and `/bin/payments refund` are governed by `/docs/returns.md`.
- `/docs/checkout.md` can still be an applied prerequisite for a 3DS or discount decision; include it when that topic BP actually applied checkout rules. Applying checkout rules includes both evaluating the line-eligibility gate and using checkout eligibility to resolve the target record before another gate decides.

## Public-record sweep

Public records named or implicated by the request are citeable and often required in every actor branch:

- Store named by id/name or read by a gate (`basket.store_id`, manager-store match) -> cite the row's `stores.record_path`.
- Catalogue SKU/product named by id/name, read by a gate, or printed as an identified public record in the final answer -> cite the row's `product_variants.record_path`. Pure availability answer sets may cite only available/passing products; that shaping does not remove refs needed for a separate identity/match claim in a non-pure availability answer, unless a stronger policy forbids citing the public record.
- `/proc/README.md` only when the request actually relies on the public manifest.

Never synthesize `/proc/...` paths from table names. Copy `record_path` from SQL or from a live `ws.read`.

## Identity-scoped SQL `record_path` column

For identity-scoped rows, a SQL `record_path` value is a filename, not clearance to cite. A customer cross-boundary branch must drop foreign basket/payment/return/customer rows (`shopping_baskets`, `payment_transactions`, `return_requests`, `customer_accounts`) and private employee/contact rows (`employee_accounts`) even if SQL returned their `record_path`.

For public rows, `record_path` is the canonical cite path. `product_variants.record_path` resolves to `/proc/catalog/<sku>.json`, not `/proc/products/<sku>.json`.

## What to include

- Request-named input artifact(s): any file/document the task instruction directs you to read (a receipt, attachment, uploaded/incoming document) and from which any part of the answer is derived. Cite its absolute live path verbatim. Path-agnostic — bind to the artifact's role, not to a specific folder like `/uploads/`.
- Active policy docs actually applied.
- The owned action target or employee action target when the branch allows it.
- Public records required by the request or by the applied gate.
- Matching policy-update/addendum docs returned by [policy_update_scan](policy_update_scan.md) when their content shaped the decision.
- For discovery tasks, every record the answer marks, one-to-one with the message.
- For non-pure availability answers that identify public catalogue products, include the `product_variants.record_path` for every product the final answer identifies, even when that product failed a stock predicate. Do not cite products merely considered and rejected if the final answer does not identify them.
- Candidate records on true clarification outcomes.

## What not to include

- Operational background / decoy docs. See [background_decoys](background_decoys.md).
- Local snapshot-mirror paths under the `vault/` prefix — refs always point at the **live** workspace, never at the read-only `vault/` copy of `/docs`, `/bin`, AGENTS/README. This exclusion is about the `vault/` mirror only; it does not cover live request paths such as `/uploads/...` or `/incoming/...`, which are real workspace objects and must be cited when the answer used them (grounding principle, class 1).
- Policy docs you opened but did not apply.
- Foreign identity-scoped `/proc/...` records on customer cross-boundary denials.
- Private contact data records unless [privacy_and_disclosure](privacy_and_disclosure.md) allows disclosure.

## Pre-submission refs checklist

Before [submission_terminal](submission_terminal.md):

1. Reconfirm actor type from `ws.id()`.
2. For every identity-scoped target in `refs`, record whether ownership passed, employee action-target exception applies, or the path must be removed.
3. Run the public-record sweep for stores and catalogue records.
4. Input-artifact check: if the task named or handed you an input file/document and any part of the answer is derived from it, that absolute live path is in `refs`.
5. Remove decoy docs and unused policy docs.
6. For discovery answers, verify `set(message_records) == set(ref_records)`. On pure availability answers, `message_records` are only the available/passing records. On non-pure availability answers, public products printed or otherwise identified in the answer remain `message_records` even if stock is zero or below the requested quantity.
7. Run the terminal message hygiene check: a blocked-outcome message must not reveal foreign identity-scoped ids or contact/profile fields learned from records. Request-named target ids and public records are different from foreign owner ids.
8. Deduplicate absolute refs.

## Complete-set discovery note

When the user asks to identify/list/mark every record in a class, the refs set must match the complete answer set, not the first useful subset. Do not use `LIMIT` on the final cohort query. For fraud/risk/anomaly discovery, use [fraud_risk_review](fraud_risk_review.md) for the cohort search and return here for final citation safety.

## Anti-patterns

- Treating every customer-actor denial as cross-boundary. Own-record capability-gap denials keep the owned target in refs.
- Dropping public store/catalogue refs because the outcome was denied early.
- Citing a foreign identity-scoped record because the SQL `record_path` column returned it.
- Answering from a document the task told you to open (an uploaded/incoming receipt, attachment, or pasted file) while citing only the downstream `/proc` records you compared it against. The input artifact is itself a required ref.
- Routing a refund refs decision through the 3DS topic doc because both use `/bin/payments`.
- Padding refs with decoy docs or unopened docs.
- Putting an answer record in the message but not in refs, or in refs but not in the message, on discovery tasks.
- Dropping a public product ref because the product failed the stock predicate in a task that is not pure availability, especially when the task asks to reference identified/matched SKUs and no policy forbids citing that public record.
- Submitting correct refs with a denial message that names a foreign owner id, customer contact field, profile detail, or coordinates; that is still a privacy failure.

## Dependencies

> If any of these dependencies change, this BP file may have become stale and must be re-derived.

- `/docs/security.md` - cross-boundary rule and personal-information disclosure boundary.
- `/bin/id` (`--help`) - actor output shape used for customer/employee/guest branching.
- SQL table `shopping_baskets` - customer ownership, store pointer, status, and canonical `record_path` for basket refs.
- SQL table `payment_transactions` - customer ownership, basket/store pointers, status, and canonical `record_path` for payment refs.
- SQL table `return_requests` - customer ownership, basket/payment pointers, status, and canonical `record_path` for return refs.
- SQL table `customer_accounts` - customer identity and contact fields that are private by default.
- SQL table `employee_accounts` - employee roster/contact fields and assigned-store scope.
- SQL table `stores` - public store `record_path` and location fields.
- SQL table `product_variants` - public catalogue `record_path` and SKU fields.
- `/proc/README.md` - source-of-truth manifest for `/proc` record families and live path roots.
