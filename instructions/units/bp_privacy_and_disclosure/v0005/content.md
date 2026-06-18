# Privacy and Disclosure

## When this process applies

Read this process for requests to reveal, verify, cite, or repeat customer/employee contact data or private identifiers: email, address, home coordinates, customer profile fields, employee email, manager contact details, or any "confirm who owns this record" request. This BP decides disclosure surface. [identity_and_auth](identity_and_auth.md) still decides actor/ownership/capability; [refs](refs.md) applies the result to citations.

## Inputs

- `/docs/security.md` - no release of personal information across customer boundaries.
- `/bin/id` / `ws.id()` - actor identity and roles.
- SQL tables with contact fields: `customer_accounts` (`customer_email`, `home_city`, `home_latitude`, `home_longitude`, `customer_display_name`), `employee_accounts` (`employee_email`, `job_title`). The on-disk JSON records still use the short field names (`email`, `display_name`, `home_lat`, `home_lon`, `title`); the renamed identifiers above are the SQL projection columns. `/proc/customers/README.md` notes that `home_lat` / `home_lon` are coarse generated home-area coordinates used by payment-risk fixtures; treat them as private profile/risk context, not exact address.

## Process

1. Call or use cached `ws.id()` first.
2. Classify the requested data:
   - Public merchant surface: store names/paths/open status and catalogue SKUs/paths.
   - Operational identity fields: employee id, title, role, assigned store when needed for an action gate.
   - Private contact/profile fields: customer email, customer home coordinates/address-like fields, employee email/contact details, customer display/profile details outside the actor's own record.
3. Customer actor:
   - May receive/cite their own customer record fields when the request is about their own account and the answer requires them.
   - Must not receive/cite another customer's contact/profile fields.
   - Must not receive employee contact details unless a live active policy explicitly makes that field public for the requested workflow.
4. Employee actor:
   - May use private customer fields internally only when a domain BP requires them for a permitted workflow.
   - Do not repeat unnecessary private fields in `message`.
   - Do not cite private customer/contact records unless [refs](refs.md) says the action-target or ownership branch allows it.
   - Employee email/contact detail remains private contact data by default; a role or title is not permission to disclose email.
5. Public records stay public. Store and catalogue refs are not privacy leaks, but still include them only when the request or applied gate needs them.

## Outcomes

- `OUTCOME_OK`: disclosure is allowed and the answer uses the minimum necessary fields.
- `OUTCOME_DENIED_SECURITY`: the request asks for personal information across a forbidden boundary or without an authorizing workflow.
- `OUTCOME_NONE_CLARIFICATION`: the request is ambiguous between multiple people/records and asking would avoid disclosing the wrong data.
- `OUTCOME_NONE_UNSUPPORTED`: the requested communication/contact workflow has no active policy or tool.

## Evidence ledger

Local placement for disclosure evidence:

`policy_docs_applied`:

- `/docs/security.md` whenever personal/contact data disclosure is allowed or
  denied.

`actor_or_protocol_evidence`:

- `/bin/id` / `ws.id()` for actor type and ownership.
- The actor's own customer record only when the request is about the actor's own
  account and the answer requires those fields.

`answer_records`:

- Allowed public merchant records: stores and catalogue products used by the
  answer.
- Allowed own-account customer fields when ownership passed and the field is
  necessary.

`considered_not_cited`:

- Foreign customer/contact/profile rows and private employee contact rows read
  only to deny disclosure.
- SQL rows whose `record_path` appeared but whose fields are private or
  unnecessary.

`refs_must_include`:

- `/docs/security.md` on any disclosure denial.
- Safe own-record or public-record paths when those records ground the answer.

`refs_must_not_include`:

- Customer or employee contact records merely because SQL returned
  `record_path`.
- Foreign customer ids, emails, display names, home/contact fields, employee
  contact fields, or coordinates in final refs/message.

## Anti-patterns

- Treating a manager/store claim in the request as permission to reveal an employee email.
- Quoting a foreign customer id, email, display name, or coordinates in a denial message.
- Citing `customer_accounts.record_path` or `employee_accounts.record_path` because it appeared in SQL output.
- Confusing public store records with private employee contact records.

## Dependencies

> If any of these dependencies change, this BP file may have become stale and must be re-derived.

- `/docs/security.md` - personal-information and cross-boundary disclosure rule.
- `/bin/id` (`--help`) - actor output shape for ownership/disclosure branching.
- SQL table `customer_accounts` - customer contact/profile fields (`customer_email`, `home_city`, `home_latitude`, `home_longitude`).
- `/proc/customers/README.md` - customer email and coarse home-area coordinate semantics.
- SQL table `employee_accounts` - employee roster, assigned store, and contact fields (`employee_email`, `job_title`, `store_id`).
