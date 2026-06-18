# Submission Terminal

## When this process applies

Read this process immediately before the final `submit_and_exit(...)` call in
every trial. This file owns the terminal protocol: final outcome validation,
post-state confirmation, the rule that execution stops after submission, and
the final `message` answer-format / token contract.

Do not use this file to decide which evidence belongs in `refs`. The topic BP
must have classified its `Evidence ledger`, and `refs.md` must have projected
safe final refs, before this process runs.

## Inputs

- Runtime terminal: `submit_and_exit(message, outcome, refs)`, injected by
  `runtime_prelude.py`.
- The already-decided `message`, `outcome`, and safe final `refs`.
- The topic BP's completed `Evidence ledger` and the shared `refs.md` checklist.

## Process

1. Confirm the narrowest topic BP has produced a final decision and that
   `scratchpad["business_process"]` names that BP.
2. Confirm the topic BP ledger has already separated `read_set`, `decision_set`,
   and final `refs`, and has classified request inputs, applied policies,
   actor/protocol evidence, action targets, answer records, post-state records,
   considered-not-cited evidence, `refs_must_include`, and
   `refs_must_not_include`.
3. Confirm final `refs` has already passed `refs.md`:
   - absolute live paths only;
   - no `vault/`, local `bin-help/`, dependency-snapshot, stale, or decoy paths;
   - no unused policy docs;
   - no foreign identity-scoped records on customer cross-boundary denials;
   - required public store/catalogue refs present;
   - every record named in a discovery answer is also in `refs`.
4. For `OUTCOME_OK` mutation tasks, re-read the mutated `/proc/...` record after
   the tool call and confirm the post-state matches the requested action and the
   topic BP's post-state rule. No post-state re-read means do not submit
   `OUTCOME_OK`.
5. For blocked outcomes, confirm no mutating tool has run. If a mutator already
   ran, a blocked outcome is no longer a valid terminal state.
6. If identity, ownership, or role shape passed but no active policy, topic BP,
   or runtime workflow supports the requested action, terminalize it as
   `OUTCOME_NONE_UNSUPPORTED`; do not invent a manual file edit or unsupported
   mutating fallback.
7. For blocked outcomes (`OUTCOME_DENIED_SECURITY`,
   `OUTCOME_NONE_UNSUPPORTED`, `OUTCOME_NONE_CLARIFICATION`), run a final
   message privacy check before submit:
   - if the actor is a customer and an ownership check failed, the message may
     name the request target id (`basket_*`, `pay_*`, `ret_*`) when the user
     supplied it, but must not reveal the foreign owner or profile fields;
   - do not repeat foreign `customer_id`, customer email, display name,
     home/contact fields, employee contact fields, or coordinates learned from
     SQL or records;
   - use generic policy wording such as "the authenticated customer does not own
     <target_id>" or "the target belongs to a different customer account";
   - keep sensitive ids in `scratchpad["decision"]` or
     `considered_not_cited`, not in `message` or unsafe `refs`.
8. Compose `message` per the **`## Answer format`** section below. Re-read the
   task instruction's `<task-instruction>` block first, then apply the
   precedence: explicit printf clause -> bare value; else a yes/no question ->
   `<YES>`/`<NO>`; else a count question -> `<COUNT:N>`; else prose.
9. Confirm the final snippet has no unresolved exploration:
   - if a `ws.read`, `ws.list`, `ws.tree`, `ws.sql_rows`, `/bin/*`, or helper
     result could change `message`, `outcome`, `refs`, or the ledger
     classification, it must have been gathered in an earlier snippet and
     reasoned over before this final call;
   - reads or SQL in the final snippet are allowed only when their returned
     values are used immediately in code to build `message`/`refs` or to assert
     post-state before `OUTCOME_OK`;
   - do not print candidate docs, policy text, ownership fields, or other still
     decisive evidence and then submit in the same snippet.
10. Call `submit_and_exit(message=..., outcome=..., refs=refs)` exactly once, as
    the last line of the final snippet.
11. After the result reports `answer_submitted=true`, do not call
    `execute_python` again.

## Answer format (message payload)

The shape of `message` is governed by a merchant reply-styling contract from
`/AGENTS.MD` ("When answering yes/no questions -- include `<YES>` or `<NO>`
tokens ... this is how the agent will know how to style the response"), with a
per-task override when the instruction prescribes an explicit literal format.
This section is the single source of truth for payload shaping; the topic BPs
and `executor_core` defer here. Apply the precedence top-down -- the first
matching rule wins:

1. **Explicit printf clause in the instruction** (`Answer in exactly format
   "%d"`, `"%s"`, `"%.2f"`, etc.) -> emit the **bare value** the placeholder
   describes. No token, no brackets, no prose, no units. Count `1` under `"%d"`
   -> `message="1"` (not `"<COUNT:1>"`, not `"1 product"`). A bare-`%s` SKU is
   the raw SKU string, no quotes unless the instruction also said to quote.
2. **Explicit literal token shown in the instruction** (the instruction text
   itself contains `<YES>` / `<NO>` / `<COUNT:N>` / `[QTY:N]` and tells you to
   emit it) -> reproduce that token byte-for-byte with its slot filled.
3. **Yes/no question** (no printf clause) -> `message` contains `<YES>` or
   `<NO>` as a literal token. This is unconditional per `/AGENTS.MD`: a yes/no
   question gets the token even though the question text never literally shows
   `<YES>`. Any explanatory prose goes around the token, not instead of it.
4. **Count question** ("how many ...?", no printf clause) -> include
   `<COUNT:N>` with the integer filled in.
5. **Otherwise** -> concise prose or a bare identifier/path. For an identifier
   or path, also put the path in `refs`.

Pre-submission check: quote the instruction's format clause (if any) verbatim.
If it gives a printf placeholder, strip any token wrapping. If it is a yes/no
question with no printf clause, confirm `<YES>`/`<NO>` is present in `message`.
Bare `yes`/`no`/`Yes.`/`No.` prose on a yes/no question is a format miss and
scores zero even when the verdict and refs are right.

## Outcomes

This BP does not choose the business outcome. It validates that the
already-selected outcome is terminally safe:

- `OUTCOME_OK` only after the request was fully answered or the mutation
  post-state was re-read.
- `OUTCOME_DENIED_SECURITY`, `OUTCOME_NONE_UNSUPPORTED`, or
  `OUTCOME_NONE_CLARIFICATION` only before any mutation. `OUTCOME_NONE_UNSUPPORTED`
  is the terminal shape when identity/ownership/role may pass but no supported
  policy/BP/runtime action path exists.
- Never intentionally submit `OUTCOME_ERR_INTERNAL`; it is a grader/runtime
  failure state.

## Evidence ledger

This BP does not add evidence buckets. It requires the invoking topic BP plus
`refs.md` to finish the ledger and final `refs` before submission.

## Anti-patterns

- Calling `execute_python` again after `submit_and_exit` already succeeded.
- Blind submit: performing exploratory reads, lists, SQL, tool calls, or policy
  scans in the same snippet as `submit_and_exit` when their result is only
  printed or left for later interpretation.
- Submitting `OUTCOME_OK` for a mutation without re-reading post-state.
- Letting this file decide whether a target record is safe to cite; that belongs
  to the topic BP ledger plus `refs.md`.
- Submitting a blocked outcome whose `message` reveals a foreign owner id,
  customer email, contact field, or coordinates learned during the investigation.
- Treating a recognized role as permission to hand-edit files when no active
  policy, topic BP, or runtime workflow supports the requested action.
- Ending the assistant turn without `submit_and_exit` after all required gates
  are resolved. If an exploratory read could still change the decision, run it
  before the terminal snippet; otherwise submit the best correct outcome.
- Emitting bare `yes`/`no` prose (or `Yes.`/`No.`) on a yes/no question instead
  of the `<YES>`/`<NO>` token, when the instruction gave no printf clause.
- Wrapping a printf-formatted (`%d`/`%s`/`%.2f`) answer in `<COUNT:N>`, `<YES>`,
  `[QTY:N]`, or any token the instruction's format clause did not call for.
- Emitting `<YES>`/`<NO>` for a question that asked for a count or a bare
  identifier.

## Dependencies

> If any of these dependencies change, this BP file may have become stale and must be re-derived.

- `runtime_prelude.py` - defines `submit_and_exit`, its `ws.answer` call, and the clean `SystemExit(0)` behavior after submission.
- `/AGENTS.MD` - source of the merchant reply-styling token contract: yes/no -> `<YES>`/`<NO>`, count -> `<COUNT:N>` ("how the agent will know how to style the response"). The `## Answer format` precedence above is derived from it. `/AGENTS.MD` is a world-only file (tracked by `world_refresh`, deliberately not a per-unit manifest dependency); if its reply-styling rule changes, this answer-format contract is stale and must be re-derived here.
