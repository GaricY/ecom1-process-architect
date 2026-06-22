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
5. Lower `priority` numbers load first within a lane queue. Use priorities to choose which packages get scarce early capacity when several assignments share a lane.
6. **Maximize expected net profit**, not just the number of delivered packages. Net profit weighs each package's margin against trip costs and penalties: late and missed packages incur penalties (per delay time, and per missed package). Use `delay_hint` to estimate expected delay/arrival.
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
- Emitting more than one JSON object, or more/fewer than one assignment per package.
- Treating `delay_hint` as a hard guarantee rather than a summary of past observations.
- Mutating commerce records — dispatch planning produces a JSON plan only.

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived.

- `/docs/dispatch.md` — the wave/package/lane model, the routing constraints, the expected-net-profit objective (margins, trip cost, delay/missed penalties), and the exact output JSON schema.
- `/docs/attachments.md` — `/uploads` as the root for the request-named wave and TSV input files.
