# bp_submission_terminal v0011

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-06-22T08:49:59+00:00`
- parent: `v0010`

## Rationale

Owning layer: terminal_protocol (wrong final yes/no message shape, not a domain or refs error). The Executor's verdict, math, and refs were all correct — old subtotal 2541.70, current 2539.10, diff 2.60, within EUR 4.00, TRUE(1), with the receipt, store, and four catalogue records cited — yet it scored 60% because the grader wanted the bare token ("Answer should be 'TRUE(1)', but at least it contains it"). The task said "Answer yes/no only" and live /AGENTS.MD says "answer exactly TRUE(1) or FALSE(2)", but the Executor padded message with a subtotal/line-item explanation. The Answer-format rule read "yes/no answers include the live yes/no token", which permitted wrapping prose around the token (the original v0006 text even said "explanatory prose goes around the token"). Fix: correct the live-/AGENTS.MD styling rule so a yes/no message is the bare token alone, extend the task-instruction rule to recognise an "answer X only" restriction, and mirror it in the pre-submission check and an anti-pattern. Class-level and grounded in live /AGENTS.MD, so it generalises to every yes/no task; the supporting figures move to scratchpad/refs. Not a regressing-PA stack: the prior PA touch (v0010) was a no-content world_refresh, so this corrects the long-standing styling wording rather than layering on a previous PA fix.

## Rollback

Create a new version from v0010 content if forcing a bare yes/no token over-trims answers that a grader expected to carry supporting prose.

## Dependencies
- `workspace:/AGENTS.MD` — Live merchant answer-styling contract; it states yes/no answers are 'answer exactly TRUE(1) or FALSE(2)', which this rule now applies as a bare-token message. Drift here must restale the terminal preflight.
- `static:static-instructions/runtime_prelude.py` — Defines submit_and_exit (message/outcome/refs terminal + SystemExit(0)) that this unit's single-call and stop rules depend on.
