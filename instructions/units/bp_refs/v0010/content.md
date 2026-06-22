# Refs

## When this process applies

Read this process whenever a `refs` list is being assembled or checked for an answer, denial, clarification, unsupported result, or final `submit_and_exit`. This file owns citation safety and evidence completeness. Use [submission_terminal](submission_terminal.md) only after `refs` is ready.

## Grounding principle

A `ref` is any object the answer is **derived from or grounded in** — cite it by its absolute **live** path (`/AGENTS.MD`: "provide full path to the object"). Three classes, ordered by how easily they are missed:

1. **Request-named input artifacts** — any file or document the task instruction itself points you to and that you read to build the answer. Bind to the role ("the task told me to read this, and I used it"), **not** to a folder name: it may live under `/storage/` (per `/docs/attachments.md`, the upload root for receipts, OCR output, customer-supplied documents), an attachment path, or a pasted document. Same boundaries as any record: an artifact tied to the current request/actor is citeable; one exposing another customer's data follows the cross-boundary/privacy branch below.
2. **Applied policy docs** — every `/docs/...` policy whose rule actually shaped the decision.
3. **Records read or identified** — identity-scoped and public `/proc/...` records, per the actor/ownership branches below.

The branches and sweeps below **refine** classes 2–3; they are not the whole universe. If the answer leans on an object that fits none of the named families, this principle still governs — cite it by its live path. Precision governs equally: cite the specific named source you used, not every neighbouring file.

## Inputs

- `/docs/security.md` — the cross-boundary and personal-information rule.
- `/bin/id` / `ws.id()` — actor type and roles.
- Request-named input artifacts — any file/document the task points you to and reads to build the answer (e.g. an uploaded receipt under `/storage/`); see the grounding principle.
- The live `/proc/...` path of every record you read — read records with `/bin/jq` / `/bin/cat` (`ws.read`). The ref is the absolute path of the JSON file itself; `/bin/sql` is unavailable, so there is no SQL `record_path` column to copy — use the live path you read.
- Topic BPs — decide which policy docs and records were actually applied.

## Actor and ownership branches

Always branch on both actor type and ownership before deciding refs:

- Customer actor (`cust_*`) on a foreign identity-scoped record: cross-boundary denial. Cite policy docs only, plus any request-named public records. Do not cite the foreign cart/payment/return record.
- Customer actor on their own record but lacking a capability: capability-gap denial on an owned record. Cite policy docs plus the owned action target and any required public records.
- Employee actor on a requested employee-shaped action: cite policy docs plus the action target even on role denial or unsupported state.
- Guest actor: no customer-owned record can pass ownership. Treat identity-scoped record requests as cross-boundary unless the task is purely public catalogue/store discovery.

Identity-scoped record families are carts (`/proc/carts`), payments (`/proc/payment-ledger`), returns (`/proc/return-workflows`), and employee contact/profile records (`/proc/employees`). Public records are catalogue products (`/proc/catalog`) and stores (`/proc/locations`).

## Topic policy docs

Include every active policy doc actually applied. Cross-boundary denials still include the topic doc because the denial is on that requested topic:

| Request shape | Topic doc |
| --- | --- |
| Basket item edit / checkout / `/bin/checkout` | `/docs/checkout.md` |
| Discount / make-good / `/bin/discount` | `/docs/discounts.md` |
| 3DS recovery / `requires_3ds_action` / payment stuck | `/docs/payments/3ds.md` |
| Return / refund approval or closure / `/bin/refund` | `/docs/returns.md` |
| Branch availability / inventory / stock-count / export | `/docs/availability-checks.md` |
| Catalogue / SKU lookup | `/docs/catalogue-lookup.md` |
| Dispatch wave planning | `/docs/dispatch.md` |

Tie-breakers:

- A 3DS recovery request may say "checkout"; a payment id or 3DS wording makes `/docs/payments/3ds.md` the topic doc.
- `/bin/refund approve` and `/bin/refund close` are governed by `/docs/returns.md`; `/bin/payments recover-3ds` is governed by `/docs/payments/3ds.md`.
- `/docs/checkout.md` can still be an applied prerequisite for a 3DS or discount decision; include it when that topic BP actually applied checkout/availability rules.

## Public-record sweep

Public records named or implicated by the request are citeable and often required in every actor branch:

- Store named by id/name or read by a gate (`cart.store_id`, manager-store match, availability query) → cite the store's live `/proc/locations/<city>/<id>.json` path.
- Catalogue SKU/product named by id/name, read by a gate, or printed as an identified public record → cite the product's live `/proc/catalog/<brand>/<sku>.json` path. Pure availability answer sets may cite only available/passing products; a separate identity/match claim still requires the public record.

Never synthesize `/proc/...` paths. Copy the live path from the record you actually read.

## Identity-scoped paths

For identity-scoped rows, having read a path is not clearance to cite it. A customer cross-boundary branch must drop foreign cart/payment/return records and private employee records even if you read them. For public rows, the live path you read is the canonical cite path: a product resolves to `/proc/catalog/<brand>/<sku>.json`, a store to `/proc/locations/<city>/<id>.json`.

## What to include

- Request-named input artifact(s): any file/document the task directs you to read (a receipt, attachment, uploaded/incoming document) and from which any part of the answer is derived. Cite its absolute live path verbatim. Path-agnostic.
- Active policy docs actually applied.
- The owned action target or employee action target when the branch allows it.
- Public records required by the request or by the applied gate.
- Matching policy-update/addendum docs returned by [policy_update_scan](policy_update_scan.md) when their content shaped the decision.
- For discovery tasks, every record the answer marks, one-to-one with the message.
- For non-pure availability answers that identify public catalogue products, include the product path for every product the final answer identifies, even when it failed a stock predicate.
- Candidate records on true clarification outcomes.

## What not to include

- Operational background / decoy docs. See [background_decoys](background_decoys.md).
- Local snapshot-mirror paths under the `vault/` prefix or any `bin-help/...` path — refs always point at the **live** workspace. This exclusion does not cover live request paths such as `/storage/...`, which are real workspace objects and must be cited when used.
- Policy docs you opened but did not apply.
- Foreign identity-scoped `/proc/...` records on customer cross-boundary denials.
- Private contact data records unless [privacy_and_disclosure](privacy_and_disclosure.md) allows disclosure.

## Pre-submission refs checklist

Before [submission_terminal](submission_terminal.md):

1. Reconfirm actor type from `ws.id()`.
2. For every identity-scoped target in `refs`, record whether ownership passed, the employee action-target exception applies, or the path must be removed.
3. Run the public-record sweep for stores and catalogue records.
4. Input-artifact check: if the task named or handed you an input file/document and any part of the answer is derived from it, that absolute live path is in `refs`.
5. Remove decoy docs and unused policy docs.
6. For discovery answers, verify `set(message_records) == set(ref_records)`. On pure availability answers, `message_records` are only the available/passing records.
7. Terminal message hygiene: a blocked-outcome message must not reveal foreign identity-scoped ids, employee contact, or profile fields. Request-named target ids and public records are different from foreign owner ids.
8. Deduplicate absolute refs.

## Complete-set discovery note

When the user asks to identify/list/mark every record in a class, the refs set must match the complete answer set, not the first useful subset. Do not cap the final cohort. For fraud/risk/anomaly discovery, use [fraud_risk_review](fraud_risk_review.md) for the cohort search and return here for final citation safety.

## Anti-patterns

- Treating every customer-actor denial as cross-boundary. Own-record capability-gap denials keep the owned target in refs.
- Dropping public store/catalogue refs because the outcome was denied early.
- Citing a foreign identity-scoped record because you read its path while resolving the request.
- Answering from a document the task told you to open (an uploaded/incoming receipt, attachment, or pasted file) while citing only the downstream `/proc` records you compared it against. The input artifact is itself a required ref.
- Routing a refund refs decision through the 3DS topic doc, or vice versa, because both touch payments.
- Padding refs with decoy docs or unopened docs.
- Putting an answer record in the message but not in refs, or in refs but not in the message, on discovery tasks.
- Submitting correct refs with a denial message that names a foreign owner id, employee contact field, or coordinates; that is still a privacy failure.

## Dependencies

> If any of these dependencies change, this BP file may have become stale and must be re-derived.

- `/docs/security.md` — cross-boundary rule and personal-information disclosure boundary.
- `/docs/attachments.md` — defines `/storage` as the request-named input-artifact root for class-1 grounding.
- `/bin/id` (`--help`) — actor output shape used for customer/employee/guest branching.
- `bin-help/sqlite_schema.txt` — record families and their live `record_path` conventions (`carts`, `payment_ledger`, `return_workflows`, `catalog`, `locations`, `staff`); replaces the removed `/proc/README.md` manifest. Identity-scoped vs public split is read from here.
