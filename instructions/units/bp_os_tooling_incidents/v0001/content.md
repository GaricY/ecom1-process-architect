# OS and Tooling Incidents

## When this process applies

A runtime tool, OS mount, temporary directory, generated index, or local command surface reports a known incident, and a documented workaround for that incident is available under `/docs/...`. Trigger phrases: a `/bin/<tool>` call that emits an "account not authorized" / "known incident" surface and points to a docs note; an OS mount, temporary-directory, or generated-index failure that names a specific incident file; any request that asks to apply a documented runtime-tool or mount workaround.

This BP owns only the workaround-use gate and its reference-the-incident-file rule. It does **not** change the domain policy, catalogue reporting rule, answer format, or ordinary grounding for the underlying request. Apply the domain BP separately for whatever the underlying task actually is ([checkout](checkout.md), [discount](discount.md), [payments_3ds_recovery](payments_3ds_recovery.md), [returns](returns.md), [product_discovery](product_discovery.md), and so on).

Not for: requests that merely quote the word "incident" or "critical" without naming a specific runtime tool / OS mount / temp directory / generated index / local command surface and a documented workaround. Those route through [background_decoys](background_decoys.md) and the dedicated domain BP.

## Inputs

- Live workspace paths:
  - `/docs/os-and-tooling-incidents-and-workarounds.md` — the authoritative workaround policy.
  - The specific incident file under `/docs/...` that documents the workaround the request would apply. The reference rule names this file as a required citation.
- Tools:
  - `/bin/id` — required by the policy before applying any workaround. Apply through [identity_and_auth](identity_and_auth.md).
  - The specific runtime tool whose `--help` (or runtime invocation) reports the incident surface. Browse `bin-help/<tool>.help.txt` to confirm the incident text and the link to the documented workaround before relying on it.

## Process

1. Apply [identity_and_auth](identity_and_auth.md) to obtain the actor from `/bin/id`. Quote-level rule from `/docs/os-and-tooling-incidents-and-workarounds.md`:

   > Run `/bin/id` before using an incident workaround.

   > If completing the request requires an incident workaround and `/bin/id` does not show an employee identity, do not run the workaround. Fail fast with `OUTCOME_DENIED_SECURITY`.

   Customer and guest actors stop here when completing the request requires the workaround. Do not apply the workaround; do not run any mutating tool that the workaround would enable.
2. Confirm the runtime tool / OS mount / temporary directory / generated index / local command actually reports the incident surface in this trial. If the surface is not present, this BP does not apply — route the request to its domain BP unchanged.
3. Locate the specific incident file under `/docs/...` that names this incident and supplies the workaround. The base policy file (`/docs/os-and-tooling-incidents-and-workarounds.md`) does not by itself satisfy the reference rule — the rule names the **specific incident file**.
4. Apply the underlying domain BP for the actual request. Quote-level rule from `/docs/os-and-tooling-incidents-and-workarounds.md`:

   > This policy controls whether a workaround may be used. It does not change the domain policy, catalogue reporting rule, answer format, or ordinary grounding requirements for the underlying request.

   Identity, ownership, state, request, post-state, and answer-format gates of the domain BP still hold.
5. When the actor is an employee and the workaround was applied to complete the request, ensure the final answer references the specific incident file. Quote-level rule:

   > If you discover a known incident and use its workaround, the final answer must reference the specific incident file that supplied the workaround.

   > The incident-file reference rule applies only for employee identities.

6. Build refs through [refs](refs.md) and submit through [submission_terminal](submission_terminal.md).

## Outcomes

- `OUTCOME_OK`: actor is an employee, a documented workaround was applied successfully, the final answer cites the specific incident file, and the underlying domain BP also reached `OUTCOME_OK` (post-state re-read where it mutated).
- `OUTCOME_DENIED_SECURITY`: completing the request requires applying a workaround and `/bin/id` does not show an employee identity. **Do not run the workaround.** Do not run any mutating tool the workaround would enable.
- `OUTCOME_NONE_UNSUPPORTED`: the incident surface is real but no documented workaround under `/docs/...` matches the case, or the underlying domain BP rules out completing the request even with the workaround.
- `OUTCOME_NONE_CLARIFICATION`: more than one candidate incident file plausibly documents the workaround and the request does not name one.

## Refs to set in scratchpad

- `/docs/os-and-tooling-incidents-and-workarounds.md` — the active policy applied to decide whether the workaround may be used. Cite on every outcome where this BP gated the decision (including the employee-only denial).
- The specific incident file under `/docs/...` that supplied the workaround — required on every `OUTCOME_OK` whose answer relied on it. The policy names this file as the required citation; the base policy alone is not enough.
- The applied domain BP's refs (target records, domain policy docs) per the domain BP's own refs section.
- Do not cite `bin-help/<tool>.help.txt` or any other local-snapshot path as a workspace doc — `bin-help/` is the local snapshot of `--help` output, not a citable workspace path.
- Apply [refs](refs.md) for final citation safety (actor/ownership branches, public-record sweep, deduplication).

## Anti-patterns

- Running a workaround as a customer or guest identity. The policy explicitly requires `OUTCOME_DENIED_SECURITY` and fail-fast in that branch.
- Citing only `/docs/os-and-tooling-incidents-and-workarounds.md` without the specific incident file on an `OUTCOME_OK` whose answer used the workaround. The reference rule names the **specific** incident file.
- Treating the OS/tooling incidents policy as a general override that relaxes domain gates (checkout stock, discount caps, 3DS state, refund role, ownership, answer format). The policy is explicit that it does not change the underlying domain rules.
- Confusing this policy with the four operational-background documents owned by [background_decoys](background_decoys.md) (`merchant-continuity-and-critical-incidents.md`, `store-associate-exception-handbook.md`, `warehouse-systems-migration-runbook.md`, `powertools-agentic-os-origin-story.md`). Those are decoys and never qualify as documented OS/tooling workarounds. The active policy `/docs/os-and-tooling-incidents-and-workarounds.md` is in the Active Decision Policies table of `/docs/README.md`; the four decoys are in the Operational Background table.
- Inferring that any `/bin/<tool>` exiting non-zero is a "known incident". A documented workaround under `/docs/...` for the specific incident must exist before this BP applies.
- Using a workaround to satisfy a request that the underlying domain BP would still block (ownership mismatch, state gate, request gate). The workaround changes only the OS/tool path, not the domain decision.

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived.

- `/docs/os-and-tooling-incidents-and-workarounds.md` — full policy text: the `/bin/id` prerequisite, the employee-only gate, the fail-fast wording, the reference-the-specific-incident-file rule, and the boundary statement that domain policy / answer format / grounding are unchanged.
- `/bin/id` (`--help`) — actor output shape consumed by [identity_and_auth](identity_and_auth.md) for the employee-only gate.
