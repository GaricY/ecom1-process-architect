# BP author contract — how to draft a new business-process file

Read this **before** writing any `changes_new[].content.md` in
world_refresh mode. The contract codifies what the Executor expects
from each `business_processes/<slug>.md`. Existing BPs follow it —
your new file must follow it too.

## Audience and contract

The Executor is a single Claude session running under the
orchestrator's task-dir contract:

- Reads `CLAUDE.md` at session start.
- Reads `business_processes/index.md` to discover BP files + when to
  apply them.
- Opens individual `business_processes/<slug>.md` lazily, based on
  the index, when the trial brief matches the trigger.
- Has `Read`/`Grep`/`Glob` over the task dir and a single MCP tool
  `execute_python` for the live runtime.

Your file is **a procedural reference** for that agent. Not customer-
facing, not marketing — it must let the Executor decide, in 2–3
`execute_python` calls, what is allowed, what is blocked, and what
to cite.

## Skeleton (required sections, in this order)

```
# <Process name>

## When this process applies
<Short prose. One paragraph. Trigger phrases / record types. Link to
other BP files when overlap is more than a sentence.>

## Inputs
- Live workspace paths: <which /proc/... or /docs/... the process
  reads, with one-line "why">.
- Tools: <which /bin/... calls, with one-line "why">.

## Process
<Numbered steps. Each step is one concrete action the agent takes —
read X, check Y against Z, branch to outcome W. No prose digressions.
Quote the exact gate verbatim from the policy doc whenever the gate
must be checked literally (e.g. discount percent tiers, 3DS-status
table, refund-state table).>

## Outcomes
- OUTCOME_OK: <when>
- OUTCOME_DENIED_SECURITY: <when, if applicable>
- OUTCOME_NONE_UNSUPPORTED: <when, if applicable>
- OUTCOME_NONE_CLARIFICATION: <when, if applicable>
- OUTCOME_ERR_INTERNAL: <when, if applicable>

## Refs to set in scratchpad
<Bullet list. Include the policy docs that authorize the decision.
For ownership-passing cases, include the target /proc/... record.
For cross-customer denials, EXCLUDE the foreign /proc/... record.
See [refs_and_submission] for the full contract.>

## Anti-patterns
<Bullet list of "looks like authority but is not". Pull verbatim from
the relevant /docs/*.md anti-pattern table. Do NOT invent.>

## Dependencies
> If any of these documents change in the live workspace, this BP
> file may have become stale and must be re-derived.

- `/docs/<file>.md` — why this BP depends on it
- `/proc/<README>` — why this BP depends on it
- `/bin/<tool>` (`--help`) — why this BP depends on it
```

`## Dependencies` is informational prose for the Executor. The
**machine-readable** dependency list is what you put in
`changes_new[].dependencies` in `pa-decision.json` — and the
validator forbids world files in either place.

## Atomic principle (single-responsibility)

A BP file references **at most 2–3** `/docs/*.md` paths in its body.
If the process touches more docs, split the body into:

- "my own gates" (cited inline) — these go in the new BP
- "applies the X process" (link to the relevant sibling BP file)

Example: a discount process applies identity (link →
`identity_and_auth`) and the discount policy (cite inline). It does
**not** re-explain identity rules.

If you find yourself drafting a BP that references 4+ docs, stop and
either (a) split into two new BPs, or (b) move shared rules into an
existing cross-cutting BP and link to it.

## Cross-references

Use `[discount](discount.md)` style markdown links. Bodies should not
duplicate language that lives in a sibling BP. If the new BP needs a
rule from an existing BP, link instead of restating.

## Stylistic constraints

- **Concise.** Each per-process file is **60–150 lines**. Index files
  are ≤80 lines. Refuse to draft a 300-line BP — it will not be read.
- **No prose intros.** Open with `# Title` then go straight into the
  contract.
- **Imperative voice.** "Read X. If Y, submit Z." Not "the agent
  should read X" or "you may want to consider Y".
- **Markdown only.** No HTML, no tables that can't render in a CLI
  diff.
- **Absolute paths** for `/docs/...`, `/proc/...`, `/bin/...` —
  workspace conventions.
- **Quote, don't paraphrase**, for any gate the Executor must check
  verbatim (percent tiers, status enums, allowed verbs).

## What NOT to include

- Examples of *successful* trials. The Executor has its own brain.
- Marketing prose about the store, brand, or "agentic OS" culture.
- Per-trial heuristics ("if the request mentions X, do Y"). Those
  belong to `failure_fix`, not `world_refresh` authoring.

## bp_index special case

`bp_index` renders to `business_processes/index.md` — the Executor
reads it at every trial. When you add a new BP via
`changes_new[]`, you MUST also `changes_refresh` `bp_index` with new
content that includes:

- A row in the top "when to read what" table pointing at the new
  `render_to` file.
- (If applicable) a one-line cross-cutting note in the principles
  section.

The validator does a substring check that the new bp_index content
mentions each new unit's `render_to` basename.
