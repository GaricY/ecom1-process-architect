# bp_os_tooling_incidents v0001

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-28T14:54:53+00:00`

## Rationale

/docs/README.md adds /docs/os-and-tooling-incidents-and-workarounds.md as a new dedicated Active Decision Policy with its own gate set: a /bin/id prerequisite, an employee-only gate, a fail-fast OUTCOME_DENIED_SECURITY on non-employee identity, a reference-the-specific-incident-file rule on the final answer, and an explicit boundary that the policy does not change domain policy / answer format / catalogue reporting rule / grounding. The new /bin/claude and /bin/codex --help surfaces are concrete in-dump examples of incident-shaped failure modes (account not authorized, points readers at the docs). No existing BP owns this workaround-use gate: identity_and_auth owns identity but not this employee-only workaround rule; background_decoys owns operational-background decoys, which is the opposite domain (active policy versus background context). The new BP is atomic and single-responsibility, links sibling BPs (identity_and_auth, refs, submission_terminal, the four mutation BPs, background_decoys) instead of restating shared logic, and is grounded entirely from current dump artifacts.

## Rollback

Remove bp_os_tooling_incidents and revert bp_index to v0003 if the new BP misroutes requests, duplicates identity/auth handling, or relaxes a domain gate by accident.

## Dependencies
- `workspace:/docs/os-and-tooling-incidents-and-workarounds.md` — Sole authority for the workaround-use policy: /bin/id prerequisite, employee-only gate, fail-fast OUTCOME_DENIED_SECURITY wording, reference-the-specific-incident-file rule, and the boundary statement that domain policy/answer-format/catalogue-reporting-rule/grounding are unchanged. The BP quotes this doc verbatim for the gate text.
- `bin_help:id.help.txt` — /bin/id is the actor source named by the policy as the prerequisite check before any workaround. The employee-only gate consumes its output shape (user prefix + roles list) via identity_and_auth.
