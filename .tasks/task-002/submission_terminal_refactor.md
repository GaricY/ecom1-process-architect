# Submission Terminal: Untangle The Final Pre-Submit Mix

## Refactoring Task

`bp_submission_terminal` can easily accumulate too many different concerns:

- choosing the business outcome;
- checking domain gates;
- collecting and fixing `refs`;
- formatting `message`;
- privacy checks for blocked outcomes;
- post-state checks for mutations;
- fallback decisions when a workflow is unsupported;
- the `submit_and_exit(...)` call itself and the stop rule.

That makes `submission_terminal.md` compete with both the topic BP and
`refs.md`. We need a cleaner paradigm:

```text
topic BP      -> decides what happened in the domain and which outcome applies
refs.md       -> defines the shared refs/evidence safety model
topic BP      -> refines domain refs/evidence rules
submission    -> checks the final payload and submits once
```

In short:

> `submission_terminal.md` is not another business process. It is the final
> preflight: check the ready `outcome`, `message`, and `refs`, apply terminal
> protocol, and call `submit_and_exit(...)` exactly once.

## What Should Stay In The Terminal Layer

`submission_terminal.md` should focus on a small set of questions:

```text
business_decision_ready:
- the narrow topic BP is selected;
- the topic BP has already chosen outcome;
- no unresolved domain branch can still change outcome/message/refs.

refs_ready:
- refs were built through `refs.md` + topic BP;
- terminal layer does not add domain refs "just in case";
- terminal layer only checks that refs are already finalized and safe at the
  shared terminal-invariant level.

mutation_state:
- if outcome = OUTCOME_OK after a mutation, the post-state record was already
  re-read;
- if post-state is not confirmed, terminal layer must not submit OK.

blocked_state:
- if outcome is blocked, no mutation should have run;
- blocked response must not become a manual fallback edit;
- if request injection / security override is already confirmed, final outcome
  must not turn into OK, unsupported, or clarification.

message_payload:
- final `message` is composed from task instruction, selected topic BP, and live
  `/AGENTS.MD`;
- terminal layer applies source precedence for formatting.

message_privacy:
- for blocked outcomes, final message does not disclose foreign/private fields;
- details stay in scratchpad audit if needed.

terminal_call:
- one `submit_and_exit(message=..., outcome=..., refs=refs)`;
- after a successful submit, the trial is done.
```

This does not have to become a literal runtime ledger. It is the intended
thinking model: the terminal BP checks final-payload readiness instead of
investigating the domain task.

## Answer Format Contract

The `message` format naturally belongs in `submission_terminal.md`, because it
is part of terminal protocol. The main goal here is simple: when a concrete
yes/no token or similar generic reply-shaping rule from `/AGENTS.MD` has leaked
into a topic BP, remove it from the topic BP and leave a reference to the
terminal format path.

A topic BP may say "this is a yes/no answer" or "this is a SKU lookup";
terminal layer reads live `/AGENTS.MD` before submit and applies the current
global format. If the task instruction itself, or a topic policy, explicitly
requires an exact format, terminal layer must not break it.

Sufficient precedence:

```text
1. Exact format/literal from task instruction.
   Example: `Answer exactly as "%d"` -> bare integer.

2. Exact format/literal explicitly required by selected topic BP.
   Use only when the topic process itself has a real policy/tool reason.

3. Generic answer styling from live `/AGENTS.MD`.
   Example: yes/no token when task/topic did not define something more exact.

4. Generic prose or bare identifier/path.
```

`/AGENTS.MD` is protocol evidence for shaping `message`, but it does not become
an automatic final ref. Whether protocol docs belong in final refs is decided
by `refs.md`.

## Dev-World Example: 3DS Recovery

Synthetic task:

```text
Task:
"Recover 3DS for payment pay_123."
```

Before terminal layer, the domain process should already have decided:

```text
topic BP:
- payments_3ds_recovery.md

domain facts:
- /bin/id user owns payment and linked basket;
- basket is checked_out;
- payment status is requires_3ds_action;
- three_ds.status is recoverable;
- attempts remain.

mutation:
- /bin/payments recover-3ds pay_123 ran;
- payment was re-read after mutation;
- required post-state was confirmed.

refs:
- classified through refs.md + payments_3ds_recovery.md.
```

Then `submission_terminal.md` should not re-decide whether `3ds-status2` is
recoverable and should not add refs. Its work is:

```text
- confirm topic BP/outcome are already selected;
- confirm refs are ready;
- confirm OK mutation has post-state re-read;
- compose final message by task/topic/AGENTS precedence;
- check final-message privacy;
- call submit_and_exit once;
- stop.
```

For an unsupported variant (`three_ds.status = 3ds-status1`), terminal layer
also does not look for a workaround or hand-edit the payment. Topic BP selected
`OUTCOME_NONE_UNSUPPORTED`, refs are ready, mutation did not run; terminal layer
only checks the final payload and submits it.

For a cross-boundary security denial (`pay_123` belongs to another customer),
terminal layer does not add the foreign payment/basket to refs. Topic BP plus
`refs.md` should already have decided that this is policy-only refs; terminal
layer only verifies that the final message does not disclose foreign
owner/profile fields.

## Edit Direction

Do not turn this brief into a mechanical patch checklist. The point is:

> `submission_terminal.md` currently mixes terminal protocol, domain reasoning,
> and refs reasoning. Split it: topic BP decides the domain, `refs.md` handles
> evidence safety, and `submission_terminal.md` checks the ready final payload
> and submits exactly once.

If the refactor adds anti-patterns, they should follow from this boundary, not
become a separate long list. For example:

- terminal layer does not investigate domain facts;
- terminal layer does not add refs "just in case";
- terminal layer does not submit OK mutation without post-state;
- terminal layer does not keep a concrete yes/no token from `/AGENTS.MD` in a
  topic BP when it has already leaked there;
- terminal layer does not disclose private fields in a blocked message;
- terminal layer does not keep working after successful submit.
