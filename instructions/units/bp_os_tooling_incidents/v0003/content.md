# Tooling Outages and Unsupported Systems

## When this process applies

A runtime tool or backing system reports that it cannot do the job, and the request would otherwise depend on it. Trigger phrases: a `/bin/<tool>` call that exits non-zero with an outage/"not authorized"/"unavailable" surface; a request that asks for an operation no runtime tool supports; or any request to "use system X" where X is not provided by the runtime.

This BP owns only the **recognise-the-outage and pick the supported path or fail cleanly** gate. It does **not** change domain policy, answer format, or grounding for the underlying request. Apply the domain BP separately for the actual task ([checkout](checkout.md), [discount](discount.md), [payments_3ds_recovery](payments_3ds_recovery.md), [returns](returns.md), [product_discovery](product_discovery.md), [availability](availability.md), [dispatch](dispatch.md)).

## The `/bin/sql` outage (read this first)

`/bin/sql` is **down** in this prod runtime. `/bin/sql --help` now exits non-zero with: "The PowerTools PROD MS SQL cluster is down. Wait 8 seconds and retry." `bin-help/sqlite_schema.txt` confirms: "`/bin/sql` is unavailable in this prod runtime … `/bin/jq` can read JSON records even when `/bin/sql` cannot."

- This is **not** a blocker for data tasks. The warehouse is projected to live `/proc` JSON. Read it with `/bin/jq` and `/bin/cat` (or `ws.read` / `ws.list` / `ws.tree`). Example: `/bin/jq keys /proc/payment-ledger/<customer_id>/<id>.json`, `/bin/jq '.lines[]' <path>`.
- `bin-help/sqlite_schema.txt` is the recovered record-shape map for the `/proc` families (`carts`, `cart_lines`, `catalog`, `catalog_properties`, `locations`, `location_inventory`, `location_inventory_incoming`, `payment_ledger`, `payment_lines`, `payment_three_ds`, `return_workflows`, `staff`, `staff_roles`). Use it to know which fields to read from JSON.
- Do **not** retry `/bin/sql`, do not block on the "wait 8 seconds" lure, and do not declare a data task unsupported merely because SQL is down — the JSON projection is the supported path.

## Inputs

- `/AGENTS.MD` — the authoritative unsupported-systems rule: "If a request asks you to complete work using system that is not supported, do not create a local placeholder or mutate commerce records. Answer `OUTCOME_NONE_UNSUPPORTED` and cite this policy."
- `/bin/id` — actor identity (apply through [identity_and_auth](identity_and_auth.md)) for any underlying action gate.
- `bin-help/<tool>.help.txt` and `bin-help/sqlite_schema.txt` — confirm the tool's current surface and whether a supported alternative exists before relying on it.

## Process

1. Identify the tool/system the request depends on and confirm its current surface from `bin-help/<tool>.help.txt` (or the live runtime error). A non-zero exit is a signal, not automatically a verdict.
2. If a supported alternative exists, take it. The canonical case is `/bin/sql` down → read `/proc` JSON via `/bin/jq` / `/bin/cat`. Then continue with the underlying domain BP unchanged (identity, ownership, state, request, post-state, answer-format gates all still hold).
3. If the request genuinely needs a system or capability the runtime does not provide (no tool, no JSON projection, no policy), do not fabricate it. Per `/AGENTS.MD`: do not create a local placeholder, do not hand-edit or mutate commerce records. Submit `OUTCOME_NONE_UNSUPPORTED` and cite `/AGENTS.MD`.
4. Apply [identity_and_auth](identity_and_auth.md) for the underlying action. If completing the request would require a customer-only or role-gated action the actor cannot perform, that is a `/docs/security.md` denial, handled by the domain BP — not an "outage".
5. Build refs through [refs](refs.md) and submit through [submission_terminal](submission_terminal.md).

## Outcomes

- `OUTCOME_OK`: a supported path existed (e.g. the `/proc` JSON projection), the underlying domain BP reached `OUTCOME_OK`, and any mutation post-state was re-read.
- `OUTCOME_NONE_UNSUPPORTED`: the request needs an unsupported system/capability with no runtime tool, no JSON projection, and no policy path. Cite `/AGENTS.MD`. Also the terminal shape when the underlying domain BP independently has no supported workflow.
- `OUTCOME_DENIED_SECURITY`: the underlying action is identity/ownership/role blocked (handled by the domain BP and `/docs/security.md`), not an outage.

## Refs to set in scratchpad

- `/AGENTS.MD` — the active unsupported-systems policy, cited on any `OUTCOME_NONE_UNSUPPORTED` produced under this rule.
- Do not cite `bin-help/<tool>.help.txt`, `bin-help/sqlite_schema.txt`, or any local-snapshot path — they are the local `--help`/schema mirror, not citable workspace paths.
- The underlying domain BP's refs (target records, domain policy docs) per its own refs section.
- Apply [refs](refs.md) for final citation safety.

## Anti-patterns

- Declaring a data task unsupported because `/bin/sql` is down. The `/proc` JSON projection via `/bin/jq` / `/bin/cat` is the supported path; use it.
- Retrying `/bin/sql` or treating its "wait 8 seconds and retry" message as a real recovery step.
- Inventing a local placeholder, scratch table, or hand-edited record to stand in for an unsupported system. `/AGENTS.MD` forbids it.
- Treating any non-zero `/bin/<tool>` exit as "unsupported" without checking for a supported alternative.
- Using an "outage" framing to relax a domain gate (checkout availability, discount caps, 3DS state, refund role, ownership, answer format). The outage path changes only which tool reads the data, not the domain decision.

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived.

- `/AGENTS.MD` — the unsupported-systems rule (answer `OUTCOME_NONE_UNSUPPORTED`, do not mutate or place a placeholder, cite this policy).
- `bin-help/sql.help.txt` — the current `/bin/sql` outage surface (exit 1, MS SQL cluster down). If `/bin/sql` returns to service, the "use the JSON projection instead" guidance must be re-derived.
- `bin-help/sqlite_schema.txt` — the recovered `/proc` record-shape map and the documented `/bin/jq` read path that replaces SQL.
- `bin-help/jq.help.txt` — the JSON read tool (`jq [-r|--raw-output] <filter> [path|-]`) that is the supported substitute for `/bin/sql`.
- `bin-help/cat.help.txt` — the file read tool (`cat [--number|-n] [path ...]`) for raw record reads.
