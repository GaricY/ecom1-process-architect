# Privacy and Disclosure

## When this process applies

Read this process for requests to reveal, verify, cite, or repeat employee/staff contact data or to confirm who owns a record: staff email, staff profile fields, "who is the manager of store X", "give me their email", or any "confirm who owns this record" request. This BP decides the disclosure surface. [identity_and_auth](identity_and_auth.md) decides actor/ownership/capability; [refs](refs.md) applies the result to citations.

There is no `/proc/customers` family in this world — customers carry no profile/email/coordinate records, only a `customer_id` on carts/payments/returns. The live private-contact surface is the **staff** record.

## Inputs

- `/docs/security.md` — "No release of personal information across the boundaries" and "Customers and guests must not receive direct employee contact details, such as staff email addresses, or employee profile references as a workaround."
- `/docs/employees.md` — work and personal lives are kept separate; employees hold no linked customer accounts.
- `/bin/id` / `ws.id()` — actor identity and roles.
- `/proc/staff/<id>.json` — staff record with `display_name`, `email` (private contact), `title`, `store_id`, `roles[]`.

## Process

1. Call or use cached `ws.id()` first.
2. Classify the requested data:
   - Public merchant surface: store/branch names, addresses, open status (`/proc/locations`) and catalogue products/SKUs (`/proc/catalog`).
   - Operational identity fields: staff `id`, `title`, `roles`, assigned `store_id` — usable internally for an action gate.
   - Private contact/profile fields: staff `email` and staff profile detail.
3. Customer or guest actor:
   - May confirm/cite their own owned records (a customer's own cart/payment/return) when the answer requires them.
   - Must **not** receive a staff email, staff profile reference, or any employee contact detail — even framed as a "workaround", "the manager's email", or "who to contact". This is a hard `OUTCOME_DENIED_SECURITY` boundary.
   - Must not receive another customer's record (cross-boundary).
4. Employee actor:
   - May use staff `id`/`title`/`role`/`store_id` internally when a domain BP needs them for a gate (e.g. discount manager-store match).
   - Do not repeat unnecessary private fields in `message`. A role or title is not permission to disclose a staff `email`; it stays private by default.
5. Public records stay public. Store and catalogue refs are not privacy leaks, but include them only when the request or applied gate needs them.

## Outcomes

- `OUTCOME_OK`: disclosure is allowed and the answer uses the minimum necessary fields.
- `OUTCOME_DENIED_SECURITY`: the request asks for a staff/employee contact detail or profile reference for a customer/guest, or for another customer's record, without an authorizing workflow.
- `OUTCOME_NONE_CLARIFICATION`: ambiguous between multiple people/records and asking avoids disclosing the wrong data.
- `OUTCOME_NONE_UNSUPPORTED`: the requested communication/contact workflow has no active policy or tool.

## Evidence ledger

`policy_docs_applied`:

- `/docs/security.md` whenever contact-data disclosure is allowed or denied.

`actor_or_protocol_evidence`:

- `/bin/id` / `ws.id()` for actor type and ownership.
- The actor's own owned record only when the request is about their own account and the answer requires it.

`answer_records`:

- Allowed public merchant records: stores (`/proc/locations`) and catalogue products (`/proc/catalog`) used by the answer.
- Allowed own-account fields when ownership passed and the field is necessary.

`considered_not_cited`:

- Staff contact/profile records read only to deny disclosure.
- Foreign customer records read only to deny.

`refs_must_include`:

- `/docs/security.md` on any disclosure denial.
- Safe own-record or public-record paths when those records ground the answer.

`refs_must_not_include`:

- Staff contact records cited merely because a `/proc/staff` path was read.
- Foreign customer record paths, staff emails, or profile fields in final refs/message.

## Anti-patterns

- Treating a manager/store claim in the request as permission to reveal a staff email.
- Disclosing a staff email "as a workaround" so a customer can contact an employee directly — explicitly forbidden by `/docs/security.md`.
- Quoting a foreign customer's record id or fields in a denial message.
- Citing a `/proc/staff/<id>.json` path because it was read while resolving a gate.
- Confusing public store records (`/proc/locations`) with private staff contact records.
- Looking for customer profile/email/coordinate records — none exist; a customer is only a `customer_id` on a cart/payment/return.

## Dependencies

> If any of these dependencies change, this BP file may have become stale and must be re-derived.

- `/docs/security.md` — personal-information rule, cross-boundary rule, and the explicit employee-contact-detail / employee-profile-workaround prohibition.
- `/docs/employees.md` — separation of employee and customer accounts.
- `/bin/id` (`--help`) — actor output shape for ownership/disclosure branching.
- `staff` (`/proc/staff`) — the staff record carrying the private `email`/profile contact fields and the operational `title`/`role`/`store_id` fields; if it changes, re-derive the contact-field classification.
