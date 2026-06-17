# Submission Terminal

## When this process applies

Read this process immediately before the final `submit_and_exit(...)` call in every trial. This file owns the terminal protocol only: final outcome validation, post-state confirmation, and the rule that execution stops after submission.

Do not use this file to decide which evidence belongs in `refs`. Build and validate the refs list with [refs](refs.md) first, then return here for the final call.

## Inputs

- Runtime terminal: `submit_and_exit(message, outcome, refs)`, injected by `runtime_prelude.py`.
- The already-decided `message`, `outcome`, and `refs`.
- The topic BP that produced the decision.

## Process

1. Confirm the narrowest topic BP has produced a final decision and that `scratchpad["business_process"]` names that BP.
2. Confirm `refs` has already been checked against [refs](refs.md):
   - absolute paths only;
   - no decoy docs;
   - no foreign identity-scoped records on customer cross-boundary denials;
   - every record named in a discovery answer is also in `refs`.
3. For `OUTCOME_OK` mutation tasks, re-read the mutated `/proc/...` record after the tool call and confirm the post-state matches the requested action. No post-state re-read means do not submit `OUTCOME_OK`.
4. For blocked outcomes, confirm no mutating tool has run. If a mutator already ran, a blocked outcome is no longer a valid terminal state.
5. Re-read the task instruction's answer format immediately before composing `message`. If it asks for a bare `%d` or `%s`, do not wrap the value in `<COUNT:...>` or any other token.
6. Call `submit_and_exit(message=..., outcome=..., refs=refs)` exactly once, as the last line of the final snippet.
7. After the result reports `answer_submitted=true`, do not call `execute_python` again.

## Outcomes

This BP does not choose the business outcome. It validates that the already-selected outcome is terminally safe:

- `OUTCOME_OK` only after the request was fully answered or the mutation post-state was re-read.
- `OUTCOME_DENIED_SECURITY`, `OUTCOME_NONE_UNSUPPORTED`, or `OUTCOME_NONE_CLARIFICATION` only before any mutation.
- Never intentionally submit `OUTCOME_ERR_INTERNAL`; it is a grader/runtime failure state.

## Refs to set in scratchpad

This BP does not add refs. It requires the topic BP plus [refs](refs.md) to finish `scratchpad["refs"]` before submission.

## Anti-patterns

- Calling `execute_python` again after `submit_and_exit` already succeeded.
- Submitting `OUTCOME_OK` for a mutation without re-reading post-state.
- Letting this file decide whether a target record is safe to cite; that belongs to [refs](refs.md).
- Ending the assistant turn without `submit_and_exit` because one more exploratory read might help. Submit the best correct blocked outcome instead of producing no answer.

## Dependencies

> If any of these dependencies change, this BP file may have become stale and must be re-derived.

- `runtime_prelude.py` - defines `submit_and_exit`, its `ws.answer` call, and the clean `SystemExit(0)` behavior after submission.
