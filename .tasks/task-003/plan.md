# Plan: Process Architect Prompt Refactor

## Goal

Make Process Architect fixes respect the refactored process boundaries instead
of patching the first BP where a failure symptom appears.

This task is about PA behavior, not about accepting PA's dev-run process fixes.
Security and free-text injection handling remain a separate follow-up task.

## Procedure

1. Review the PA outputs produced before this prompt refactor:
   - `.tasks/task-001/pa_fix_run_20260618-034209/`
   - `.tasks/task-003/pa_fix_run_20260618-121140/`
   - `.tasks/task-003/pa_fix_run_20260618-142842/`

2. Identify the recurring failure mode:
   - PA over-explains and stacks broad prose fixes where one narrow rule is
     enough;
   - PA treats the first failing BP as the owner even when the true owner is a
     different layer;
   - PA does not sufficiently notice when a prior PA fix caused a later score
     regression, so it layers another fix instead of replacing or narrowing the
     bad one.

3. Update PA prompts, not business-process content:
   - `instructions/prompts/process_architect/failure_fix.md`
   - `instructions/prompts/process_architect/world_refresh.md`
   - `instructions/prompts/process_architect/refresh.md`

4. Add an explicit owning-layer classification before edits:
   - `domain_policy` and `topic_evidence` belong in the narrow topic BP;
   - `refs_safety` belongs in `refs.md`;
   - `terminal_protocol` belongs in `submission_terminal.md`;
   - `routing` belongs in `bp_index`.

5. Tighten PA's edit discipline:
   - prefer one narrow owner and one narrow change;
   - keep final reports concise;
   - do not move a rule into another layer just because that is where the
     symptom appeared;
   - when a recent PA-created version made later scores worse, consider
     replacing or narrowing that version instead of stacking another fix.

6. Temporarily restore the active process versions to the commit state used by
   the original `pa_fix_run_20260618-034209` comparison point, then run PA_fix
   again with the new prompts. Archive the largest useful comparison run as
   `.tasks/task-003/pa_fix_run_20260618-211756/`.

7. Compare new PA outputs against the pre-refactor PA outputs:
   - check whether PA selected the correct owning layer;
   - check whether it wrote a narrow fix rather than task-specific overfit;
   - check whether conflict rebases preserved earlier orthogonal fixes;
   - check whether out-of-scope classes, especially security/free-text
     injection, are still being proposed as active process changes.

## Result

The prompt refactor improved PA ownership behavior:

- `t52` moved from an overfit `bp_product_discovery` OCR-matching fix to the
  correct shared `bp_refs` request-named-input citation fix.
- `t40` and `t48` stayed in the fraud topic BP and avoided the earlier
  cardinality-rule oscillation.
- `t55` moved from `bp_submission_terminal` to the shared safety owner, but the
  proposed free-text/security rule is still out of scope for this task and
  should remain archived rather than accepted here.

The remaining follow-up is a separate security task for free-text and planted
content handling.
