# Refs

## When this process applies

Read this process whenever evidence is being classified or a final `refs` list
is being assembled for an answer, denial, clarification, unsupported result, or
`submit_and_exit`. This file owns the shared Evidence ledger model and the safe
projection into final citations. Topic BPs own the domain-specific placement of
their records, policies, and post-state reads into that model.

## Evidence ledger model

Keep these three sets separate:

- `read_set`: everything opened, listed, grep-searched, returned by SQL, or
  read through a tool. This is an audit trail, not a citation list.
- `decision_set`: evidence that actually shaped `message`, `outcome`,
  mutation/no-mutation, scope, count, cohort membership, or denial reason.
- `refs`: the safe final citation projection from `decision_set`, expressed as
  absolute live workspace paths and stripped of forbidden/private/decoy/stale
  paths.

`refs` is not `read_set`. `refs` is also not always all of `decision_set`: a
foreign identity-scoped record can be load-bearing for a security denial but
still forbidden in final `refs` and `message`.

Before final submission, classify evidence by role. The executor does not need
literal JSON, but the scratchpad reasoning must make the buckets clear enough
to audit.

`request_named_inputs`:

- Files, attachments, pasted docs, receipt/OCR/report paths, or other input
  artifacts the task explicitly told you to read.
- If any answer fact came from such an input, cite the absolute live input path
  unless a privacy rule forbids it. This is a shared invariant owned here, not a
  per-topic rule: cite the input even when the answer compares it against
  downstream records (catalogue rows, store rows, etc.) and the topic BP's
  `refs_must_include` enumerates only those downstream records.

`policy_docs_applied`:

- `/docs/...` policies whose rules shaped outcome, message, mutation/no-mutation,
  report schema, or citation semantics.
- Matching policy-update/addendum docs returned by `policy_update_scan` when
  their content shaped the decision.
- Do not cite docs opened only during discovery if their rules did not apply.

`actor_or_protocol_evidence`:

- `/bin/id` result and, when needed, the actor's own employee/customer record
  used for role, ownership, store scope, or issuer identity.
- `/AGENTS.MD` when the live answer-format or merchant reply protocol shaped
  `message`. Protocol files are normally scratchpad evidence, not automatic
  final refs; cite them only when a process or the task treats that protocol as
  grounding evidence for the answer.

`action_targets`:

- Concrete basket/payment/return/discount/etc. records the requested workflow
  acts on or refuses to act on.
- Whether a target may be cited depends on actor type, ownership, public/private
  status, and the topic BP's local rules.

`answer_records`:

- Records whose facts directly determine an information answer, cohort, count,
  status, eligibility, or unsupported result.
- For list/count/cohort tasks, this is the answer cohort or aggregate evidence,
  not arbitrary examples.

`post_state_records`:

- Records re-read after an allowed mutation to prove the requested state changed
  and still satisfies the policy's post-state requirements.
- Required before any `OUTCOME_OK` mutation submission. If the post-state path
  is the same as an action target, cite the path once and keep the re-read proof
  in scratchpad.

`considered_not_cited`:

- Records read only to reject a candidate, disambiguate, or audit a false lead.
- Foreign/private records that shaped a denial but are unsafe in final refs or
  message.
- Background, decoy, stale, local snapshot, and tool-help paths.

`refs_must_include`:

- Categories and concrete paths the shared rules plus the topic BP require in
  final `refs` for the selected outcome branch.

`refs_must_not_include`:

- Categories and concrete paths forbidden in final `refs`, even if read or
  load-bearing in the internal decision.

## Inputs

- `/docs/security.md` - cross-boundary and personal-information rule.
- `/bin/id` / `ws.id()` - actor type and roles.
- Request-named input artifacts - any file/document the task points to and that
  the answer used.
- SQL `record_path` columns - canonical cite paths for safe rows. Every table
  exposes `record_path`; the old `path` column name no longer exists.
- Topic BPs - decide which policy docs and records were actually applied.

## Actor and ownership branches

Always branch on both actor type and ownership before projecting refs:

- Customer actor (`cust_*`) on a foreign identity-scoped record:
  cross-boundary denial. Cite policy docs only, plus any request-named public
  records. Do not cite the foreign basket/payment/return/customer record.
- Customer actor on their own record but lacking a capability: capability-gap
  denial on an owned record. Cite policy docs plus the owned action target and
  any required public records.
- Employee actor on a requested employee-shaped action: cite policy docs plus
  the action target even on role denial or unsupported state. The target is the
  work item the employee was asked to handle.
- Guest actor: no customer-owned record can pass ownership. Treat
  identity-scoped record requests as cross-boundary unless the task is purely
  public catalogue/store discovery.

Identity-scoped record families include baskets, payments, returns, customers
(SQL tables `shopping_baskets`, `payment_transactions`, `return_requests`,
`customer_accounts`), and employee contact/profile details (`employee_accounts`).
Public records include catalogue products (`product_variants`) and stores.

## Topic policy docs

Include every active policy doc actually applied. Cross-boundary denials still
include the topic doc because the denial is on that requested topic:

| Request shape | Topic doc |
| --- | --- |
| Checkout / place order / `/bin/checkout` | `/docs/checkout.md` |
| Discount / make-good / `/bin/discount` | `/docs/discounts.md` |
| 3DS recovery / `pay_*` stuck / `requires_3ds_action` | `/docs/payments/3ds.md` |
| Return / refund / `ret_*` / refund status tokens | `/docs/returns.md` |

Tie-breakers:

- A 3DS recovery request may say "checkout"; a `pay_*` id or 3DS wording makes
  `/docs/payments/3ds.md` the topic doc.
- `/bin/payments recover-3ds` is governed by `/docs/payments/3ds.md`;
  `/bin/payments approve-refund` and `/bin/payments refund` are governed by
  `/docs/returns.md`.
- `/docs/checkout.md` can still be an applied prerequisite for a 3DS or discount
  decision; include it only when that topic BP's local ledger says checkout
  rules were actually applied.

## Public-record sweep

Public records named or implicated by the request are citeable and often
required in every actor branch:

- Store named by id/name or read by a gate (`basket.store_id`,
  manager-store match) -> cite the row's `stores.record_path`.
- Catalogue SKU/product named by id/name, read by a gate, or printed as an
  identified public record in the final answer -> cite
  `product_variants.record_path`. Pure availability answer sets may cite only
  available/passing products; non-pure identity/match answers keep refs for
  products the message identifies unless a stronger policy forbids them.
- `/proc/README.md` only when the request actually relies on the public
  manifest.

Never synthesize `/proc/...` paths from table names. Copy `record_path` from SQL
or from a live `ws.read`.

## Identity-scoped SQL `record_path` column

For identity-scoped rows, a SQL `record_path` value is a filename, not clearance
to cite. A customer cross-boundary branch must drop foreign
basket/payment/return/customer rows (`shopping_baskets`, `payment_transactions`,
`return_requests`, `customer_accounts`) and private employee/contact rows
(`employee_accounts`) even if SQL returned their `record_path`.

For public rows, `record_path` is the canonical cite path.
`product_variants.record_path` resolves to `/proc/catalog/<sku>.json`, not
`/proc/products/<sku>.json`.

## Final refs projection

Project final `refs` only after the topic BP ledger has identified
`refs_must_include` and `refs_must_not_include` for the outcome branch.

Include:

- Safe request-named input artifacts that the answer used.
- Applied policy docs and matched policy updates.
- Safe action targets, answer records, public records, and post-state records
  required by the topic BP.
- Candidate records on true clarification outcomes when the actor may see those
  candidates.

Do not include:

- Operational background / decoy docs. See `background_decoys.md`.
- Local snapshot-mirror paths under `vault/`, local `bin-help/...` paths, or
  world-baseline/dependency-snapshot paths. Refs always point at the live
  workspace.
- Policy docs opened but not applied.
- Foreign identity-scoped `/proc/...` records on customer cross-boundary
  denials.
- Private contact/profile records unless `privacy_and_disclosure.md` and the
  topic BP allow disclosure.
- Rejected candidates, false leads, stale docs, or examples not used by the
  final answer.

## Pre-submission refs checklist

Before `submission_terminal.md`:

1. Reconfirm actor type from `ws.id()`.
2. Confirm the topic BP ledger has classified request inputs, applied policies,
   actor/protocol evidence, action targets, answer records, post-state records,
   considered-not-cited evidence, `refs_must_include`, and
   `refs_must_not_include` for the selected outcome branch.
3. For every identity-scoped target in final refs, record whether ownership
   passed, the employee action-target exception applies, or the path was
   removed.
4. Run the public-record sweep for stores and catalogue records.
5. Request-named-input backstop (apply even when the topic BP ledger never
   classified an input): if the task named or handed you an input file/document
   - an upload, receipt, OCR/report dump, or pasted doc path - and any answer
   fact is derived from it, its absolute live path MUST be in final `refs`
   unless a privacy rule forbids it. A comparison answer that reads the input
   for one side and catalogue/records for the other still cites the input; the
   downstream records it was compared against do not replace it.
6. Remove decoy docs, local snapshot paths, unused policy docs, rejected
   candidates, and unsafe foreign/private records.
7. For discovery answers, verify `set(message_records) == set(ref_records)`.
   On pure availability answers, `message_records` are only available/passing
   records. On non-pure availability answers, public products identified in the
   answer remain `message_records` even if stock is zero or below the requested
   quantity.
8. Run the terminal message hygiene check: blocked-outcome messages must not
   reveal foreign identity-scoped ids or contact/profile fields learned from
   records. Request-named target ids and public records are different from
   foreign owner ids.
9. Deduplicate absolute refs.

## Complete-set discovery note

When the user asks to identify/list/mark every record in a class, the refs set
must match the complete answer set, not the first useful subset. Do not use
`LIMIT` on the final cohort query. For fraud/risk/anomaly discovery, use
`fraud_risk_review.md` for the cohort search and return here for final citation
safety.

## Anti-patterns

- Treating every customer-actor denial as cross-boundary. Own-record
  capability-gap denials keep the owned target in refs.
- Treating `refs` as everything opened or queried.
- Citing a foreign identity-scoped record because SQL returned `record_path`.
- Answering from a request-named input artifact while citing only downstream
  records compared against it.
- Routing a refund refs decision through the 3DS topic doc because both use
  `/bin/payments`.
- Padding refs with decoy docs, local `vault/` paths, local `bin-help/` paths,
  stale snapshot paths, or unopened docs.
- Putting an answer record in the message but not in refs, or in refs but not in
  the message, on discovery tasks.
- Dropping public store/catalogue refs because the outcome was denied early.
- Submitting correct refs with a denial message that names a foreign owner id,
  customer contact field, profile detail, or coordinates.

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
