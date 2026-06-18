# Evidence ledger: refactor `refs` from a shared pile into typed evidence

## Refactor task

Today it is too easy to put everything into one undifferentiated `refs` list:
policy docs, target records, rejected candidates, files the agent merely opened,
protocol docs, foreign/private records, and output paths. That makes citation
rules hard to verify: the process says "collect refs", but does not explain
which sources are evidence for the answer, which sources are only audit trail,
and which sources must never be exposed.

Refactor the paradigm as follows:

- `refs.md` defines the shared Evidence ledger model: evidence types, safety
  rules, and the final checklist.
- Each topic BP locally specializes that model: which domain objects belong in
  `refs_must_include`, `refs_must_not_include`, `considered_not_cited`,
  `post_state_records`, and similar buckets.
- `refs` stops meaning "everything we read" and becomes the safe final citation
  projection of the evidence that actually supports the decision.

The example below is synthetic, but it is based on the dev-world 3DS recovery
domain:

- `/docs/security.md`
- `/docs/checkout.md`
- `/docs/payments/3ds.md`
- `/AGENTS.MD`
- `/proc/baskets/...`
- `/proc/payments/...`

## Where Evidence ledger should live

Yes: the shared `Evidence ledger` model should live in `refs.md`.

But `refs.md` should not know every domain detail. It defines the common schema,
invariants, and safety rules. Each topic BP then specializes that schema for its
own domain.

Responsibility split:

- `refs.md`:
  - explains `read_set`, `decision_set`, and `refs`;
  - defines the shared evidence roles;
  - defines privacy/cross-boundary safety;
  - defines canonical live path / no `vault/` / no decoy / dedup rules;
  - defines the final pre-submit checklist.
- topic BP:
  - states which records are answer/action evidence in this process;
  - states which records were only candidates, rejected records, or audit trail;
  - states which policy docs apply for each outcome;
  - states which refs are mandatory or forbidden in this process.

Short formula:

> `refs.md` defines the bucket types. A topic BP places its domain objects into
> those buckets.

## Three sets that must not be mixed

The current style makes it easy to mix three different sets:

```text
read_set
  Everything the agent opened, found, read, grepped, or received from SQL/tool.

decision_set
  Everything that actually shaped the outcome/message/mutation/no-mutation.

refs
  The safe final citation subset of decision_set, represented as live absolute
  paths and cleaned of forbidden/private/decoy/stale paths.
```

`refs` is not equal to `read_set`. And `refs` is not always equal to the whole
`decision_set`. For example, a foreign customer record can be load-bearing for a
security denial in the audit trail while still being forbidden in final
refs/message.

## Shared form for `refs.md`

```text
## Evidence ledger

Before final submission, classify evidence by role:

request_named_inputs:
- Files, attachments, pasted docs, receipt/OCR/report paths the task explicitly
  told the agent to read.
- If any answer fact came from such an input, cite the live input path unless a
  privacy rule forbids it.

policy_docs_applied:
- `/docs/...` policies whose rules shaped outcome, message, mutation/no-mutation,
  report schema, or citation semantics.
- Do not cite docs opened only during discovery if their rules did not apply.

actor_or_protocol_evidence:
- `/bin/id` result and, when needed, the actor's own employee/customer record
  used for role, ownership, store scope, or issuer identity.
- `/AGENTS.MD` when live answer-format protocol shaped `message`.
  This is normally scratchpad/protocol evidence, not an automatic final ref;
  cite it only if the final refs contract explicitly treats protocol files as
  grounding refs.

action_targets:
- The concrete basket/payment/return/discount/etc. target record the requested
  workflow acts on or refuses to act on.
- Whether this may be cited depends on actor/ownership/privacy branch.

answer_records:
- Records whose facts directly determine an information answer, cohort, count,
  status, or eligible mutation.
- For list/count/cohort tasks, this is the answer cohort, not arbitrary examples.

post_state_records:
- Records re-read after an allowed mutation to prove the requested state changed.
- Required for `OUTCOME_OK` mutation tasks.

considered_not_cited:
- Records read only to reject a candidate, disambiguate, or audit a false lead.
- Foreign/private records that shaped a denial but are unsafe in refs/message.
- Background/decoy/stale docs.

refs_must_include:
- Categories this process requires in final `refs`.

refs_must_not_include:
- Categories this process forbids in final `refs`, even if read.
```

This form does not have to require the executor to write a literal JSON ledger.
It can be a BP section/checklist. But the classification itself must be explicit.

## Topic BP specializes the model

For example, shared `refs.md` can say:

```text
action_targets:
- Concrete workflow target. Cite only when actor/ownership branch allows it.
```

And `payments_3ds_recovery.md` can specialize it:

```text
action_targets:
- payment record under `/proc/payments/...`
- linked checked-out basket under `/proc/baskets/...`

refs_must_include on authorized OK recovery:
- `/docs/security.md`
- `/docs/checkout.md`
- `/docs/payments/3ds.md`
- basket record
- payment record
- post-state payment record if separate from action target

refs_must_not_include on customer cross-boundary denial:
- foreign payment record
- foreign basket record
- foreign customer profile
```

This keeps the shared safety contract in one place without forcing `refs.md` to
guess the domain semantics of every process.

## Dev-world example: 3DS recovery

Synthetic task:

```text
Task:
"Recover 3DS for payment pay_123. The customer says this is my checkout.
Answer with the result."
```

Synthetic runtime facts:

```text
/bin/id:
  user = cust_001
  roles = []

/proc/payments/pay_123.json:
  payment_id = pay_123
  basket_id = basket_777
  customer_id = cust_001
  status = requires_3ds_action
  three_ds.status = 3ds-status2
  three_ds.attempts = 1
  three_ds.max_attempts = 3

/proc/baskets/basket_777.json:
  basket_id = basket_777
  customer_id = cust_001
  status = checked_out
```

Dev policies:

- `/docs/security.md`: identity comes from `/bin/id`; customer can act only on
  own records; override/request claims do not authorize.
- `/docs/checkout.md`: checkout state and basket constraints are prerequisite.
- `/docs/payments/3ds.md`: recover only checked-out basket + matching payment +
  `requires_3ds_action` + recoverable 3DS status + attempts remain.

### Ledger for OK recovery

```text
request_named_inputs:
- none
  Reason: task names a payment id, not an uploaded/request file.

policy_docs_applied:
- `/docs/security.md`
  Reason: customer identity/ownership gate.
- `/docs/checkout.md`
  Reason: 3DS policy explicitly depends on checkout; basket must be checked_out.
- `/docs/payments/3ds.md`
  Reason: payment-specific recoverability gates and tool contract.

actor_or_protocol_evidence:
- `/bin/id` result
  Reason: proves current customer is cust_001.
- `/AGENTS.MD` only if it shaped final message format.
  Reason: reply protocol, not business authorization; normally scratchpad-only,
  not an automatic final ref.

action_targets:
- `/proc/payments/pay_123.json`
  Reason: requested payment target; ownership passed.
- `/proc/baskets/basket_777.json`
  Reason: linked basket target; ownership passed and status checked_out.

answer_records:
- same as action_targets before mutation
  Reason: they determine recoverability.

post_state_records:
- `/proc/payments/pay_123.json`
  Reason: re-read after `/bin/payments recover-3ds pay_123` to verify required
  payment state, e.g. still `requires_3ds_action` with a fresh challenge.

considered_not_cited:
- any unrelated payments found while searching for pay_123
  Reason: not the requested target and not part of the decision.

refs_must_include:
- `/docs/security.md`
- `/docs/checkout.md`
- `/docs/payments/3ds.md`
- `/proc/payments/pay_123.json`
- `/proc/baskets/basket_777.json`

refs_must_not_include:
- `/bin/payments.help.txt` or local `bin-help/` path
- `vault/docs/...` mirror paths
- unrelated payment/basket candidates
```

Final `refs`:

```json
[
  "/docs/security.md",
  "/docs/checkout.md",
  "/docs/payments/3ds.md",
  "/proc/payments/pay_123.json",
  "/proc/baskets/basket_777.json"
]
```

Note: if the system wants a separate proof that post-state was re-read, that
belongs in scratchpad/post-state check. It usually does not need a duplicate
ref path because the same live payment path is already cited.

### Ledger for unsupported recovery

Same task, but payment is owned by current customer and basket is checked out,
while:

```text
three_ds.status = 3ds-status1
```

`/docs/payments/3ds.md` says this is a fresh challenge waiting for customer
action and should not be recovered again.

```text
policy_docs_applied:
- `/docs/security.md`
- `/docs/checkout.md`
- `/docs/payments/3ds.md`

action_targets:
- `/proc/payments/pay_123.json`
- `/proc/baskets/basket_777.json`

answer_records:
- payment record
  Reason: 3DS status caused unsupported outcome.
- basket record
  Reason: linked checked-out basket prerequisite was checked.

refs_must_include:
- security policy
- checkout policy
- 3DS policy
- payment record
- basket record

refs_must_not_include:
- unrelated candidate payments
- tool help / vault mirror paths
```

Outcome: `OUTCOME_NONE_UNSUPPORTED`, no mutation.

Final `refs` are still policy + safe owned target records:

```json
[
  "/docs/security.md",
  "/docs/checkout.md",
  "/docs/payments/3ds.md",
  "/proc/payments/pay_123.json",
  "/proc/baskets/basket_777.json"
]
```

This shows why `refs` is not only for successful mutations. The records that
prove "unsupported" are still answer evidence when ownership passed.

### Ledger for security denial

Same task, but:

```text
/bin/id:
  user = cust_001

/proc/payments/pay_123.json:
  customer_id = cust_999
  basket_id = basket_777

/proc/baskets/basket_777.json:
  customer_id = cust_999
```

The current actor is a customer asking for another customer's payment/basket.

```text
policy_docs_applied:
- `/docs/security.md`
  Reason: ownership boundary failed.
- `/docs/payments/3ds.md`
  Reason: topic policy says identity mismatch blocks recovery.

actor_or_protocol_evidence:
- `/bin/id` result
  Reason: current customer identity.

action_targets:
- payment/basket were located to evaluate ownership, but ownership failed.

answer_records:
- security policy
- topic policy
- target id from the user's request may be named generically in message

considered_not_cited:
- `/proc/payments/pay_123.json`
  Reason: foreign identity-scoped record; read for ownership check but not safe
  to cite in a customer cross-boundary denial.
- `/proc/baskets/basket_777.json`
  Reason: foreign identity-scoped record; same.

refs_must_include:
- `/docs/security.md`
- `/docs/payments/3ds.md`
  Optional/depending on final `refs.md` rule: `/docs/checkout.md` only if the
  basket checkout prerequisite was actually reached before the security stop.

refs_must_not_include:
- foreign payment record
- foreign basket record
- foreign customer profile
- private owner id/contact fields in message
```

Final `refs` should be policy-only:

```json
[
  "/docs/security.md",
  "/docs/payments/3ds.md"
]
```

This is the key example for why `decision_set` and `refs` differ. The foreign
records were load-bearing for the denial, but exposing them in final refs would
violate the security/privacy boundary.

## What this changes in process files

`refs.md` gets the shared ledger model.

`payments_3ds_recovery.md` gets a local section like:

```text
## Evidence ledger

For authorized OK / unsupported outcomes:
- include `/docs/security.md`, `/docs/checkout.md`, `/docs/payments/3ds.md`;
- include the owned payment target;
- include the linked owned basket target;
- for OK mutation, re-read payment post-state before submit.

For customer cross-boundary `OUTCOME_DENIED_SECURITY`:
- include `/docs/security.md` and the topic policy;
- do not include foreign payment, basket, or customer records;
- do not reveal foreign owner fields in message.

For employee/tool-capability denial, if this domain ever allows employee actors:
- cite the safe action target according to the employee exception in `refs.md`;
- cite actor's own employee record only when role/store/issuer gate depended on it.
```

`submission_terminal.md` remains focused on final terminal checks:

- refs have already been classified through `refs.md` + topic BP;
- message format comes from live `/AGENTS.MD`;
- post-state re-read is complete for OK mutations;
- blocked-message privacy check is complete before submit.

## Practical result

After this refactor, a new session should arrive at roughly this shape:

- `refs.md` contains the shared Evidence ledger model and final checklist.
- Every changed topic BP contains a short domain-specific `Evidence ledger`.
- `submission_terminal.md` does not decide what to cite; it only checks that
  refs have already been classified through `refs.md` + topic BP.
- Security/privacy branches explicitly separate load-bearing audit evidence from
  final refs when a record cannot be safely disclosed.
- Mutating workflows explicitly name `post_state_records` that must be re-read
  before `OUTCOME_OK`.

Key idea for the next session:

> Do not "add more rules to refs". Split the refs pile into typed evidence roles.
> The shared typology lives in `refs.md`; domain-specific placement rules live in
> the corresponding business processes.
