# Submission Terminal

## When this process applies

Read this process immediately before the final `submit_and_exit(...)` call in every trial. This file owns the terminal protocol: final outcome validation, post-state confirmation, the rule that execution stops after submission, and the **final `message` answer-format / token contract** (the `## Answer format` section below — the single source of truth for `TRUE(1)`/`FALSE(0)` / SKU / bare-value payload shaping).

Do not use this file to decide which evidence belongs in `refs`. Build and validate the refs list with [refs](refs.md) first, then return here.

## Inputs

- Runtime terminal: `submit_and_exit(message, outcome, refs)`, injected by `runtime_prelude.py`.
- The already-decided `message`, `outcome`, and `refs`.
- The topic BP that produced the decision.
- `/AGENTS.MD` — the merchant reply-styling contract (yes/no token, SKU-lookup answer rule).

## Process

1. Confirm the narrowest topic BP has produced a final decision and that `scratchpad["business_process"]` names that BP.
2. Confirm `refs` has already been checked against [refs](refs.md): absolute live paths only; no decoy docs; no `vault/` or `bin-help/` paths; no foreign identity-scoped records on customer cross-boundary denials; every record named in a discovery answer is also in `refs`.
3. For `OUTCOME_OK` mutation tasks, re-read the mutated `/proc/...` record (via `/bin/jq` / `/bin/cat` / `ws.read`) after the tool call and confirm the post-state matches the requested action. No post-state re-read means do not submit `OUTCOME_OK`.
4. For blocked outcomes, confirm no mutating tool has run and no record was hand-edited. If a mutator already ran, a blocked outcome is no longer a valid terminal state.
5. If identity, ownership, or role shape passed but no active policy, topic BP, or runtime workflow supports the requested action (including when the request needs a capability the runtime cannot provide, e.g. `/bin/sql` is down), terminalize as `OUTCOME_NONE_UNSUPPORTED`; do not invent a manual file edit or unsupported mutating fallback. See [os_tooling_incidents](os_tooling_incidents.md).
6. For blocked outcomes (`OUTCOME_DENIED_SECURITY`, `OUTCOME_NONE_UNSUPPORTED`, `OUTCOME_NONE_CLARIFICATION`), run a final message privacy check before submit:
   - if the actor is a customer and an ownership check failed, the message may name the request target id when the user supplied it, but must not reveal the foreign owner or profile fields;
   - do not repeat a foreign `customer_id`, employee email, display name, contact fields, or coordinates learned from records;
   - use generic policy wording such as "the authenticated customer does not own the target record";
   - keep sensitive ids in `scratchpad["decision"]` for audit, not in `message`.
7. Compose `message` per the **`## Answer format`** section below. Re-read the task instruction's `<task-instruction>` block first, then apply the precedence.
8. Confirm the final snippet has no unresolved exploration: any `ws.read`, `ws.list`, `ws.tree`, `/bin/*`, or helper result that could change `message`/`outcome`/`refs` must have been gathered earlier and reasoned over. Reads in the final snippet are allowed only when their values are used immediately to build `message`/`refs` or to assert post-state before `OUTCOME_OK`.
9. Call `submit_and_exit(message=..., outcome=..., refs=refs)` exactly once, as the last line of the final snippet.
10. After the result reports `answer_submitted=true`, do not call `execute_python` again.

## Answer format (message payload)

The shape of `message` is governed by the **merchant reply-styling contract** in `/AGENTS.MD`. This section is the single source of truth for payload shaping; the topic BPs and `executor_core` defer here. Apply the precedence top-down — the first matching rule wins:

1. **Explicit printf clause in the instruction** (`Answer in exactly format "%d"`, `"%s"`, `"%.2f"`, etc.) → emit the **bare value** the placeholder describes. No token, no brackets, no prose, no units. A bare-`%s` SKU is the raw SKU string.
2. **Explicit literal token shown in the instruction** (the instruction text itself contains a token such as `TRUE(1)` / `FALSE(0)` / a `[QTY:N]` slot and tells you to emit it) → reproduce that token byte-for-byte with its slot filled.
3. **Yes/no question** (no printf clause) → answer **exactly `TRUE(1)`** for yes or **`FALSE(0)`** for no. From `/AGENTS.MD`: "For yes/no answers, answer exactly `TRUE(1)` or `FALSE(0)`." This is the literal token a yes/no answer must carry, even when the question text never shows it. Any explanatory prose goes around the token, not instead of it.
4. **SKU lookup** → from `/AGENTS.MD`: "For SKU lookups, answer with `OUTCOME_OK` and the SKU only when exactly one product matches." Emit the single matching SKU as the bare value. If the request is ambiguous between products, submit `OUTCOME_NONE_CLARIFICATION`, ask which product the user meant, and cite every candidate product record (see [product_discovery](product_discovery.md)).
5. **Otherwise** → concise prose or a bare identifier/path (e.g. a count as a bare integer). For an identifier or path, also put the path in `refs`.

Pre-submission check: quote the instruction's format clause (if any) verbatim. If it gives a printf placeholder, strip any token wrapping. If it is a yes/no question with no printf clause, confirm `TRUE(1)` / `FALSE(0)` is present in `message`. Bare `yes`/`no`/`Yes.`/`No.` prose on a yes/no question is a format miss and scores zero even when the verdict and refs are right.

## Outcomes

This BP does not choose the business outcome. It validates the already-selected outcome is terminally safe:

- `OUTCOME_OK` only after the request was fully answered or the mutation post-state was re-read.
- `OUTCOME_DENIED_SECURITY`, `OUTCOME_NONE_UNSUPPORTED`, or `OUTCOME_NONE_CLARIFICATION` only before any mutation. `OUTCOME_NONE_UNSUPPORTED` is the terminal shape when identity/ownership/role may pass but no supported policy/BP/runtime path exists.
- Never intentionally submit `OUTCOME_ERR_INTERNAL`; it is a grader/runtime failure state.

## Refs to set in scratchpad

This BP does not add refs. It requires the topic BP plus [refs](refs.md) to finish `scratchpad["refs"]` before submission.

## Anti-patterns

- Calling `execute_python` again after `submit_and_exit` already succeeded.
- Blind submit: exploratory reads/tool calls in the same snippet as `submit_and_exit` when their result is only printed or left for later interpretation.
- Submitting `OUTCOME_OK` for a mutation without re-reading post-state.
- Letting this file decide whether a target record is safe to cite; that belongs to [refs](refs.md).
- Submitting a blocked outcome whose `message` reveals a foreign owner id, employee contact field, or coordinates.
- Hand-editing a `/proc/...` record as an "unsupported fallback" when no tool/policy supports it.
- Emitting `<YES>` / `<NO>` / `<COUNT:N>` or bare `yes`/`no` prose on a yes/no question. The current world token is `TRUE(1)` / `FALSE(0)` — those older tokens are retired.
- Wrapping a printf-formatted (`%d`/`%s`/`%.2f`) answer in any token the instruction's format clause did not call for.

## Dependencies

> If any of these dependencies change, this BP file may have become stale and must be re-derived.

- `runtime_prelude.py` — defines `submit_and_exit`, its `ws.answer` call, and the clean `SystemExit(0)` after submission.
- `/AGENTS.MD` — source of the merchant reply-styling contract: yes/no → `TRUE(1)`/`FALSE(0)`, SKU lookup → bare SKU on a single match / `OUTCOME_NONE_CLARIFICATION` otherwise. The `## Answer format` precedence is **derived from it**. `/AGENTS.MD` is a world-only file (tracked by `world_refresh`); if its reply-styling rule changes — different tokens, removal, or a new answer type — this contract is stale and must be re-derived here.
