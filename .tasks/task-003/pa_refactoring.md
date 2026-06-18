# PA Refactor: Keep Process Architect From Mixing Layers Again

## Summary

After the manual refactor of `refs.md`, topic Evidence ledger sections, and
`submission_terminal.md`, the PA prompts need a small hardening pass:

```text
instructions/prompts/process_architect/failure_fix.md
instructions/prompts/process_architect/world_refresh.md
instructions/prompts/process_architect/refresh.md
```

PA must not fix a symptom in the first BP that happens to fail. Before editing,
it must answer one question: **which layer owns this problem?**

## Main PA Split

```text
domain_policy
  Gates, statuses, workflows, tool calls, exact policy wording.
  Owner: narrow topic BP.

topic_evidence
  Which domain records/docs are evidence for the answer.
  Owner: topic BP Evidence ledger.

refs_safety
  Shared refs rules: privacy, cross-boundary disclosure, live absolute paths,
  decoys, deduplication, request-named input class.
  Owner: refs.md.

terminal_protocol
  Final message shape, submit preflight, post-state before OK mutation,
  one submit call, stop after submit.
  Owner: submission_terminal.md.

routing
  Which BP should be read for a request.
  Owner: bp_index.
```

This does not mean "move everything about refs into `refs.md`." In particular:

- "which discount/3DS/checkout records are evidence?" belongs to the topic BP;
- "may a foreign customer record be cited?" belongs to `refs.md`;
- "final yes/no token, bare `%d`, or exactly one submit" belongs to
  `submission_terminal.md`.

## Prompt Changes

Add this short rule to all three prompts:

```text
Before editing a unit, classify the issue by owning layer:
domain_policy / topic_evidence / refs_safety / terminal_protocol / routing.
Edit the owning layer. Do not move a rule into another layer just because that
is where the failure symptom appeared.
```

For `failure_fix.md`:

- missing or extra refs do not automatically mean "edit `refs.md`";
- first decide whether the problem is a shared safety invariant or domain
  evidence classification;
- a wrong final token or message shape is usually terminal protocol, not the
  topic BP;
- a domain gate, status, or tool mistake is usually the topic BP.

For `world_refresh.md`:

- `/AGENTS.MD` drift in the answer-format section is a terminal-protocol
  signal;
- policy-doc drift that changes a domain workflow or evidence model is a topic
  BP signal;
- policy/doc drift that changes shared citation/privacy semantics is a
  `refs.md` signal, followed by checking affected topic ledgers;
- do not add `/AGENTS.MD` as an ordinary dependency to every unit.

For `refresh.md`:

- this mode can edit only one stale unit;
- if the correct owner is another unit, do not force the foreign rule into the
  current unit;
- leave the current unit unchanged or only refresh its local stale wording, and
  make the neighboring owner clear in the rationale.

## Mini Examples

```text
Wrong yes/no token
-> terminal_protocol
-> submission_terminal.md
```

```text
Missing refs because the topic answer cohort was underspecified
-> topic_evidence
-> the corresponding topic BP Evidence ledger
```

```text
Missing refs because the shared privacy/cross-boundary model is wrong
-> refs_safety
-> refs.md
```

```text
New status, tool verb, or report schema in policy/tool docs
-> domain_policy
-> narrow topic BP
```

## Short Goal

The PA prompts should keep PA from rebuilding the old mixed model:

> Classify the owning layer first, then edit the prose.
