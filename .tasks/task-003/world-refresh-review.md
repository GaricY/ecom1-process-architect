# Review: world_refresh run 20260619-011800

## Scope

Reviewed PA workdir:

`20260619-011800/0001-t01-vm2-LytsXNjnYw2VdsQ498f45ZY7TcC-process-architect-world-refresh-v0004`

This review is limited to the task-003 prompt/process behavior: whether Process
Architect respected the refactored owning-layer boundaries. I am not evaluating
manifest dependency mechanics here; those belong to the orchestrator/apply
layer and should be reviewed separately.

## Short Verdict

Yes, this result matches our expectations for the task-003 PA prompt refactor.

The important signal: PA did not smear the new `/docs/security.md` account
recovery rule across `identity_and_auth`, `refs`, `submission_terminal`, or
existing payment/checkout BPs. It classified the drift as `domain_policy`, made
a new narrow topic BP, and touched `bp_index` only for routing.

That is the behavior we wanted from the owning-layer prompt change.

## What Changed In The World

PA correctly identified one new mutating domain:

- new tool help:
  `/bin/account-recovery send-email-link <customer_id> <destination_email>`;
- `/bin/README.md`: the tool mechanically creates outgoing account email-change
  verification requests and does not enforce `/docs/security.md`;
- `/run/actions/README.md`: action-file convention
  `/run/actions/account-recovery-<customer_id>.json`;
- `/docs/security.md`: account recovery / email-change verification is a
  customer-only action, and links may be sent only for the account matching
  `/bin/id`.

There were no relocations, no removals, and no drafts to ground/merge/prune.

## PA Decision

PA produced:

- `changes_new`: `bp_account_recovery`
- `changes_refresh`: `bp_index` from `v0007`
- `unchanged`: the other 15 registered BPs
- `advance_baseline: true`

Applied versions:

- `bp_account_recovery/v0001`
- `bp_index/v0008`
- `world_baseline/v0005`

## Owning-Layer Assessment

### Good: Correct Owner

The drift superficially looks like a security/identity change because
`/docs/security.md` changed. Before the task-003 prompt refactor, this is the
kind of signal PA could have pushed into `identity_and_auth` or duplicated
across several existing BPs.

It did not do that in this run. The decision explicitly says:

`domain_policy -> new narrow topic BP`

That is the right layer. Account recovery has:

- a new mutating tool;
- its own request shape;
- a customer-only gate;
- a concrete output file;
- a required post-state read;
- routing ambiguity with the existing word `recovery`.

This is a distinct atomic domain, not just new prose for the shared identity
layer.

### Good: Small Change Surface

The changed surface is appropriate:

- new `bp_account_recovery`;
- refreshed `bp_index` route and cross-cutting note;
- no `executor_core` change;
- no `identity_and_auth` change;
- no `refs` change;
- no `submission_terminal` change;
- no `payments_3ds_recovery` change.

This is the main task-003 success signal. PA did not patch the first BP where a
symptom appeared.

### Good: Existing BPs Were Reviewed, Not Ignored

The `unchanged` explanations are meaningful rather than empty boilerplate. PA
explicitly checked the likely false owners:

- `identity_and_auth`: general identity rules did not change; the new rule
  belongs to the topic BP;
- `privacy_and_disclosure`: disclosure semantics did not change;
- `refs`: no new shared citation/privacy semantics;
- `submission_terminal`: no terminal protocol drift;
- `payments_3ds_recovery`: overlap on the word `recovery` is handled by
  routing, not by changing the 3DS BP.

That matches the task-003 target pattern: classify the owner, then edit only
the owner.

## New BP Content Assessment

`bp_account_recovery` is directionally correct:

- applies `identity_and_auth` first;
- requires customer identity from `/bin/id`;
- denies guest/employee actors;
- denies cross-customer account recovery;
- does not treat request text, VIP/incident/recovery wording, or authority bait
  as authorization;
- uses `/bin/account-recovery send-email-link <customer_id> <destination_email>`;
- re-reads `/run/actions/account-recovery-<customer_id>.json` before
  `OUTCOME_OK`;
- forbids hand-editing `/run/actions`;
- disambiguates account recovery from payment 3DS recovery;
- allows destination email to differ from the on-file email, which is correct
  for email-change verification.

The evidence/refs placement is also clean enough: policy doc, actor evidence,
action target, and post-state record are described in the topic ledger, while
shared citation safety remains delegated to `refs.md`.

## Minor Reservations

These are not prompt-process failures, but they are worth recording:

1. `bp_account_recovery` is conservative about not naming a foreign account id
   in denied messages/refs. That is probably safe and consistent with the
   current cross-boundary denial style, but future evals may show whether
   request-supplied target ids need a more nuanced message rule.

2. The BP invokes `policy_update_scan` before mutation. That matches current
   process style, but this small domain may not strictly need it. It is not
   harmful unless it causes unnecessary searching in practice.

3. `pa-decision.json` includes `/run/actions/README.md` as a dependency for the
   new BP, but the applied manifest currently does not show it. I treat this as
   manifest/apply mechanics, not as PA prompt-process behavior.

4. `bp_index` has empty dependencies. Same category: likely current
   version/apply mechanics, not evidence that PA chose the wrong layer.

## Does This Match Task-003 Expectations?

Yes.

Task-003 wanted PA to:

- classify the owning layer before editing;
- avoid moving rules into the BP where the symptom merely appeared;
- prefer one narrow owner and one narrow change;
- avoid broad defensive rewrites;
- keep `refs_safety` in `refs.md`, `terminal_protocol` in
  `submission_terminal.md`, `routing` in `bp_index`, and domain policy in a
  narrow topic BP.

This run does that.

The strongest positive signal is that PA left `identity_and_auth` untouched even
though the changed policy file was `/docs/security.md`. It recognized the
security edit as a new domain-specific action policy, not as a reason to
rewrite the shared identity model.

## Recommendation

Do not change the PA prompts based on this run.

For the prompt-process aspect, this is a successful world-refresh example. The
next review should focus on:

- actual executor behavior on account-recovery tasks;
- whether `bp_account_recovery` needs a small content adjustment after runtime
  evidence;
- separate orchestrator/apply mechanics for manifest dependencies and refs.

