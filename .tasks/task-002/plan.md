# Plan: `submission_terminal` Refactor

## Goal

Finish the responsibility split after the Evidence ledger refactor:

- the topic BP chooses the domain outcome and domain evidence/refs buckets;
- `refs.md` owns shared evidence/citation safety;
- `submission_terminal.md` owns only the final preflight for an already-built
  payload and exactly one `submit_and_exit(...)`.

In other words, `submission_terminal.md` must not become another business
process that re-investigates the domain, patches refs, or overrides the topic
BP decision.

## What Is Already Partly Done

Task 001 already introduced the key parts of this split:

- `bp_submission_terminal/v0006` already says refs must be classified through
  the topic BP plus `refs.md` before the terminal layer.
- `bp_index/v0006` already separates the outcome token from the answer-payload
  shape and points to `submission_terminal.md` as the single home for payload
  formatting.
- `executor_core/v0015` already delegates refs-model details to `refs.md` plus
  the topic BP and should not substantively repeat terminal payload rules.

This is not enough yet: `bp_submission_terminal/v0006` still enumerates too many
evidence buckets / refs checks, and some topic BPs still contain concrete
payload tokens (`<YES>`, `<NO>`, format wording). Those should either become an
"answer kind" or remain only as an explicit literal from the task instruction.

## Edit Plan

1. Fix the terminal-layer boundary in a new `bp_submission_terminal` version:
   - `business_decision_ready`: topic BP is selected, outcome is already chosen,
     and no unresolved domain branch remains;
   - `refs_ready`: refs were already projected through `refs.md` plus the topic
     BP; terminal does not add domain refs "just in case";
   - `mutation_state`: `OUTCOME_OK` after mutation is allowed only after a
     post-state re-read;
   - `blocked_state`: a blocked outcome is invalid after a mutation and does not
     become a manual fallback edit;
   - `message_payload`: terminal applies precedence across task literal / topic
     exact requirement / live `/AGENTS.MD` / generic prose;
   - `message_privacy`: final message does not disclose private/foreign fields;
   - `terminal_call`: exactly one `submit_and_exit(...)`, then stop.

2. Slim down `bp_submission_terminal`:
   - remove detailed refs bucket enumeration that belongs in `refs.md`;
   - keep only terminal-level checks that refs are ready and safe by the
     referenced processes;
   - remove domain fallback decisions when they repeat topic BP ownership;
   - keep answer-format precedence as the main terminal-layer responsibility.

3. Audit active topic BPs for payload-format leakage:
   - find generic `<YES>/<NO>/<COUNT:N>` and "answer format" rules outside
     `submission_terminal.md`;
   - replace generic wording with "this is a yes/no answer", "this is a count
     answer", or "this is an identifier/path answer", with a reference to the
     terminal format path;
   - do not remove explicit literal requirements when they genuinely come from
     the task instruction or topic policy, but phrase them as input to terminal
     payload shaping rather than as an independent submit contract in the topic
     BP.

4. Check the primary candidates first:
   - `bp_returns`: state lookup currently says to answer `<YES>/<NO>` directly;
   - `bp_product_discovery`: claim verification contains concrete `<YES>/<NO>`
     wording and a `message=...` example; split the verdict / required
     identifier from generic terminal formatting;
   - `executor_core`: make sure `## Answer format` is only a thin pointer to
     `submission_terminal`, without a copied rule set.

5. Check the legacy surface:
   - `bp_refs_and_submission` still has an active manifest, but is not present
     in `instructions/registry.json`, so it is not rendered into task dirs;
   - do not touch it in this task unless necessary, but after the edits verify
     that the active rendered process set does not reference
     `refs_and_submission.md`.

6. Release changes only as new versions under `instructions/units/<id>/vNNNN/`.
   Do not edit committed versions in place. Do not commit until a separate
   command.

## Verification

- `git diff` / staged review should show only the task-002 plan and new
  instruction versions.
- `preflight_instruction_store` should pass through the project `.venv`.
- Active rendered processes should not reference `refs_and_submission.md`.
- Active topic BPs should not retain generic answer-token rules, except for
  references to `submission_terminal.md` or explicit-literal descriptions from
  task instruction/policy.
- `bp_submission_terminal` should not reclassify refs buckets or make domain
  decisions instead of the topic BP.

## Out Of Scope

- Do not run benchmark/PA_fix without separate approval.
- Do not solve prompt-injection/free-text safety; that is a separate task.
- Do not change algorithmic domain rules unless they are tied to the terminal
  boundary.
