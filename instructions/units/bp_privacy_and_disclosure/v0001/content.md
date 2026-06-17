# Privacy and Disclosure

## When this process applies

Read this process for requests to reveal, verify, cite, or repeat customer/employee contact data or private identifiers: email, address, home coordinates, customer profile fields, employee email, manager contact details, or any "confirm who owns this record" request. This BP decides disclosure surface. [identity_and_auth](identity_and_auth.md) still decides actor/ownership/capability; [refs](refs.md) applies the result to citations.

## Inputs

- `/docs/security.md` - no release of personal information across customer boundaries.
- `/bin/id` / `ws.id()` - actor identity and roles.
- SQL tables with contact fields: `customers`, `employees`.

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

## Refs to set in scratchpad

- Always include `/docs/security.md` when denying disclosure.
- Include the actor's own customer record only when ownership passed and the data is necessary.
- Do not include customer or employee contact records merely because SQL returned their `path`.
- Delegate final citation safety to [refs](refs.md).

## Anti-patterns

- Treating a manager/store claim in the request as permission to reveal an employee email.
- Quoting a foreign customer id, email, display name, or coordinates in a denial message.
- Citing `customers.path` or `employees.path` because it appeared in SQL output.
- Confusing public store records with private employee contact records.

## Dependencies

> If any of these dependencies change, this BP file may have become stale and must be re-derived.

- `/docs/security.md` - personal-information and cross-boundary disclosure rule.
- `/bin/id` (`--help`) - actor output shape for ownership/disclosure branching.
- SQL table `customers` - customer contact/profile fields.
- SQL table `employees` - employee roster, assigned store, and contact fields.
