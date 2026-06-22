# Dispatch Planning

## When this process applies

A request to **plan a dispatch wave** that points you at a dispatch wave `.md` file. `/AGENTS.MD`: "When asked to plan a dispatch wave and pointed to a `.md` file, read that file and follow `/docs/dispatch.md`." This is an information/planning task — the deliverable is a single JSON assignment object, not a commerce mutation. Do not mutate carts/payments/inventory.

## Inputs

- Live workspace paths:
  - The dispatch wave `.md` file named by the request (typically under `/uploads`; see `/docs/attachments.md`). It names the **package TSV** and **lane TSV** for that wave.
  - The package TSV and lane TSV the wave file names.
  - `/docs/dispatch.md` — the authoritative planning policy and output schema.
- Tools: `/bin/id`; `/bin/cat` to read the wave file and TSVs. SQL is unavailable.

## Process

From `/docs/dispatch.md`:

1. Read the wave file first; it names the package TSV and lane TSV. Read both TSVs.
2. Package rows define the item to move, the source store (`from_store_id`), the destination store (`to_store_id`), the delivery due time, and the margin earned if the package arrives.
3. Lane rows define directed transport links: origin, destination, capacity per trip, ETA, trip cost, and `delay_hint` (a summary of past delay observations).
4. Build a route per package: it must **start at the package `from_store_id` and end at `to_store_id`**, using direct or multiple hub lanes, where every consecutive lane connects (each lane's destination is the next lane's origin).
5. `capacity` is **per trip**, not a cap on how many packages may ever use a lane. A lane is a queue across trips: several assignments may share it, lower `priority` numbers load first, and any assignment beyond the per-trip `capacity` simply waits for the next trip. Set `priority` so the tightest-`due_time` / highest-margin packages on a shared lane load first. Do **not** divert a package onto a costlier or more delay-prone route merely because a cheaper shared lane is already at its per-trip `capacity` — share the lane and order the queue with `priority`; divert only when the expected next-trip wait would push that package past its `due_time` by more than the cheaper route saves.
6. **Maximize expected net profit across the whole wave — a lane's `cost_cents` is the cost of one *trip*, not a per-package charge.** One trip on a lane carries up to its `capacity` packages for a single `cost_cents`; the plan's transport cost is `Σ over each used lane of ceil(packages routed over it / capacity) × cost_cents`. So the *marginal* transport cost of routing a package over a lane that another assignment already rides — while that trip still has spare `capacity` — is **zero**, and a dedicated lane carrying one package pays its full `cost_cents` alone. Optimize the wave's total expected net (`Σ margins − Σ trip costs − Σ expected late penalties`), not each package's cost in isolation.
   - Schedule buffer = `due_time − Σ lane eta`. The late penalty is charged per unit of delay, and a route's *actual* arrival is its nominal ETA **plus** whatever delay its lanes' `delay_hint`s imply — so buffer is a safety margin, not a guarantee. Thin, zero, or negative buffer, and `likely`/`often` or `medium`/`long when delayed` hints, raise expected lateness; an extra hop raises it only to the extent that lane can independently delay.
   - **Selection rule:** prefer the route that adds the least *marginal* trip cost while keeping comfortable buffer and low delay risk — which usually means **consolidating packages onto shared hub lanes** (each extra rider on an already-paid, spare-`capacity`, low-delay-risk lane is nearly free) rather than buying a dedicated direct lane. Do **not** reject a low-delay-risk shared hub route in favour of an expensive dedicated direct lane merely because it has fewer hops; extra hops cost expected late penalty (delay risk), not nominal trip cost. Conversely, do not trade away buffer or route a high-margin package through a `likely`/`long when delayed` lane to save cost — even a modest chance of arriving late outweighs the saving. Pay for a dedicated direct lane or a fresh extra trip only when consolidation would push a package past its `due_time` (or add more expected late penalty than the trip cost it saves).
   - When no route can arrive by `due_time`, choose the one with the least expected lateness; keep a package assigned only while its expected net (after the expected penalty) stays positive.
7. Return **exactly one** JSON object with **one assignment per package**:

   ```json
   {
     "assignments": [
       {"package_id": "XFER-001", "route": ["lane-a", "lane-b"], "priority": 1}
     ]
   }
   ```

8. The JSON object is the answer payload; [submission_terminal](submission_terminal.md) owns the final emission. Do not wrap or reshape it beyond what `/docs/dispatch.md` specifies.

## Outcomes

- `OUTCOME_OK`: a valid assignment object covering every package with connected routes from `from_store_id` to `to_store_id`, priorities set, optimized for expected net profit.
- `OUTCOME_NONE_CLARIFICATION`: the request does not name a wave file, or the wave file does not name its TSVs.
- `OUTCOME_NONE_UNSUPPORTED`: the named wave/TSV inputs are missing or unreadable, or no connected route exists for a required package (state which packages cannot be routed).

## Evidence ledger

`request_named_inputs`:

- The dispatch wave `.md` file and the package/lane TSVs it names. Their live paths are load-bearing answer evidence.

`policy_docs_applied`:

- `/docs/dispatch.md` when its routing/optimization/schema rules shaped the answer.

`answer_records`:

- The wave file and the two TSVs that determine the assignments.

`refs_must_include`:

- `/docs/dispatch.md` and the request-named wave/TSV input paths the plan was built from.

`refs_must_not_include`:

- Commerce records (`/proc/...`) not used by the plan, and `bin-help` paths.

`post_state_records`:

- none; this BP does not mutate.

## Anti-patterns

- Building a route whose lanes do not connect from `from_store_id` to `to_store_id`.
- Optimizing for delivered-package count instead of expected net profit (ignoring trip cost and late/missed penalties).
- Treating a lane's `capacity` as a hard cap on total assignments and diverting a package onto a costlier or more delay-prone route to avoid sharing — `capacity` is per trip; share the lane and order the queue with `priority`, letting overflow wait a trip unless that wait would miss `due_time`.
- Charging a lane's `cost_cents` per package instead of per *trip* — trip cost is shared across the up-to-`capacity` packages on one trip, so a per-package model overstates shared hub routes and drives packages onto expensive dedicated direct lanes. Price the *marginal* trip cost and consolidate onto lanes other packages already ride.
- Sacrificing schedule buffer, or routing a high-margin package through a `likely`/`long when delayed` lane, to save trip cost — or using `delay_hint` only as a tie-breaker — which is how a high-margin package picks up an avoidable late penalty.
- Emitting more than one JSON object, or more/fewer than one assignment per package.
- Treating `delay_hint` as a hard guarantee rather than a summary of past observations.
- Mutating commerce records — dispatch planning produces a JSON plan only.

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived.

- `/docs/dispatch.md` — the wave/package/lane model, the routing constraints, the per-trip capacity/priority queue semantics, the per-trip (shared-capacity) trip-cost model and expected-net-profit objective (margins, trip cost, delay/missed penalties), and the exact output JSON schema.
- `/docs/attachments.md` — `/uploads` as the root for the request-named wave and TSV input files.
