# OS and Tooling Incidents

## When this process applies

A runtime tool or mount reports that it is unavailable or degraded — most concretely, `/bin/sql` exits non-zero with "The PowerTools PROD MS SQL cluster is down". In the current world there is **no** `/docs` workaround policy and **no** documented incident file: `/docs/os-and-tooling-incidents-and-workarounds.md` was removed, and the `/bin/claude` / `/bin/codex` "Embrace AI" surfaces no longer exist. This BP no longer authorizes any workaround; it only records how the one live degradation is handled and routes everything else to its domain BP.

## Inputs

- Live workspace paths:
  - `/AGENTS.MD` — the unsupported-system rule, cited when a request depends on an unavailable tool with no alternative.
  - `bin-help/sqlite_schema.txt` — its header tells you whether SQL is available. When it begins "`# Warehouse schema — reconstructed from the live /proc projection.`", `/bin/sql` is down and `/proc` JSON is the source of truth.
- Tools: `/bin/id` (identity, via [identity_and_auth](identity_and_auth.md)).

## Process

1. There is no documented OS/tooling workaround to apply. Do not invent onboarding, eligibility, or workaround steps, and do not treat a tool exiting non-zero as a "known incident with a workaround".
2. **The one live degradation — `/bin/sql` cluster-down — has a documented alternative, not a workaround:** read `/proc/<family>/.../*.json` records directly (per the executor core's degraded-runtime guidance, signalled by the reconstructed-projection schema header). Use that path; do not retry `/bin/sql`.
3. For any other unavailable/unauthorized tool with no runtime alternative, the request is unsupported: do not hand-mutate commerce records; answer `OUTCOME_NONE_UNSUPPORTED` and cite `/AGENTS.MD`.
4. Apply the underlying domain BP for the actual request normally. A tooling degradation never relaxes identity, ownership, state, request, or answer-format gates.

## Outcomes

- `OUTCOME_OK`: the request was completed via the documented data path (read `/proc` when SQL is down) and the underlying domain BP also reached `OUTCOME_OK`.
- `OUTCOME_NONE_UNSUPPORTED`: the request depends on a tool that is unavailable/unauthorized and has no runtime alternative; cite `/AGENTS.MD`.
- `OUTCOME_DENIED_SECURITY`: per the domain BP / [identity_and_auth](identity_and_auth.md) when an identity/ownership gate fails.

## Evidence ledger

`policy_docs_applied`:

- `/AGENTS.MD` when a request was unsupported because a required tool is unavailable.
- The underlying domain BP's policy docs remain separate and still required.

`actor_or_protocol_evidence`:

- `/bin/id`; the tool's degradation surface is decision evidence but `bin-help` paths are not final refs.

`refs_must_include`:

- `/AGENTS.MD` on the unsupported branch; otherwise the applied domain BP's required refs.

`refs_must_not_include`:

- `bin-help` paths and the (removed) legacy incident/workaround docs.

`post_state_records`:

- per the underlying domain BP.

## Anti-patterns

- Inferring that any `/bin/<tool>` exiting non-zero is a "known incident" with a workaround — no `/docs` workaround policy exists in this world.
- Retrying `/bin/sql` or probing it repeatedly when the schema header shows the reconstructed `/proc` projection — read `/proc` instead.
- Chasing an "Embrace AI" / onboarding / store-manager approval path — those tools and that lure no longer exist.
- Using a "tooling incident" as a reason to relax a domain gate (checkout stock, discount cap, 3DS state, refund role, ownership, answer format).

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived. If a real `/docs` OS/tooling-workaround policy reappears, rebuild the workaround gate.

- `/AGENTS.MD` — the unsupported-system rule cited when a required tool is unavailable.
- `bin-help/sqlite_schema.txt` — its header signals whether `/bin/sql` is available or the `/proc` projection must be read directly.
- `/bin/id` (`--help`) — actor classification via [identity_and_auth](identity_and_auth.md).
