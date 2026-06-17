# Conflict-mode failure_fix

This is your SECOND pass. While you were thinking, another Process
Architect published a new version of a unit you tried to edit. Your
first-pass draft is preserved in `pa-output-draft/` (read-only — do
not edit there). The orchestrator now expects you to reconcile your
change against the new latest version and rewrite `pa-output/`.

## What happened

For every unit listed in `conflict-context.json` (in the workdir root):

- `your_base_version` — the version you originally branched from
  (what the Executor read at trial time).
- `new_latest` — the version that landed while you were drafting.
- The new latest is mirrored under `version-history/units/<unit_id>/<new_latest>/`
  with `content.md`, `changes.md`, and `diff.patch`.

## Your task

For each conflicted unit:

1. **Read the other PA's reasoning.**
   `version-history/units/<unit_id>/<new_latest>/changes.md` (their
   rationale) + `content.md` (the new active text). Skim `diff.patch`
   only if the textual change matters — usually the rationale tells
   you enough.

2. **Re-read your own failure context.** Your draft is in
   `pa-output-draft-NN/`. Don't anchor on the draft text — anchor on
   the failure it was responding to (`failure-fix-task.md`,
   `.logs/executor_actions.md`).

3. **Re-think the BP, don't merge two patches.** The other PA was
   solving the same BP failure from a different angle; they're not
   your opponent. Ask: given both failure scenarios, what should
   this BP say next? Answer that question, then write it. The output
   should read like a single coherent edit, not a reconciliation of
   two competing edits. Stay within the brevity rules from your mode
   prompt (modify existing rules over adding new ones; keep the
   total length sane).

   Tag the outcome per unit:
   - `subsumed` — their version already covers what you would have
     said. NO new version of this unit is written; you MUST list
     the unit in `subsumed[]` with a one- to three-sentence
     rationale citing the specific passage(s) of their `<new_latest>`
     that absorb your concern. Skipping the rationale is rejected.
   - `extended` — their version is right; you'd add a specific point
     they missed. Write the extended content under
     `pa-output/units/<unit_id>/content.md`; add an entry to
     `changes[]` with `conflict_resolution.outcome = "extended"`.
   - `replaced` — their version misses the root cause you saw.
     Write a fresh version addressing both failures; add an entry
     to `changes[]` with `conflict_resolution.outcome = "replaced"`
     and a one-sentence justification in `rationale` for why their
     change alone was insufficient.

   Default to `subsumed` or `extended`. `replaced` is rare.

4. **Rewrite `pa-output/pa-decision.json`.**
   - `mode = "failure_fix"`.
   - `changes[]`: one entry per `extended` / `replaced` unit. Each
     has the standard fields PLUS `conflict_resolution`:
     `{"original_base": "<vNNNN>", "rebased_onto": "<vMMMM>",
       "outcome": "extended" | "replaced"}`.
   - `subsumed[]`: one entry per dropped unit:
     `{"unit_id": "...", "your_original_base": "<vNNNN>",
       "current_latest": "<vMMMM>", "rationale": "..."}`.
   - Every unit listed in `conflict-context.json` MUST appear in
     exactly one of `changes[]` or `subsumed[]`. Coverage is enforced
     by the validator; gaps reject the decision.
   - Non-conflicted units from your first pass keep their original
     `base_version` and stay in `changes[]` without
     `conflict_resolution`.

   Minimal example with one subsumed unit:

   ```json
   {
     "mode": "failure_fix",
     "changes": [],
     "subsumed": [
       {
         "unit_id": "bp_refs_and_submission",
         "your_original_base": "v0009",
         "current_latest": "v0011",
         "rationale": "v0011 rule 4 already lists the per-record invariant shape with the observed-vs-store worked example; my edit would have re-stated the same point."
       }
     ]
   }
   ```

5. **Pre-submission preflight** (same as your mode prompt's
   pre-submission checklist): every declared dependency Read, siblings
   re-read, prior `changes.md` re-read for every unit you edit.

When done, end your turn. Orchestrator validates + applies under the
unit write lock. If a third PA published in the meantime, you may be
invoked again (up to `PA_CONFLICT_MAX_RETRIES`).
