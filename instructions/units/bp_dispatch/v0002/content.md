# Dispatch Wave Planning

## When this process applies

A request to **plan a dispatch wave** that points to a dispatch wave `.md` file. `/AGENTS.MD`: "When asked to plan a dispatch wave and pointed to a `.md` file, read that file and follow `/docs/dispatch.md`." This is a planning/optimization task that returns a routing plan as JSON. It does not mutate commerce records. Not for branch availability/stock (see [availability](availability.md)) or for any basket/payment/return action.

## Inputs

- Request-named input artifacts (the task points you to these — typically under `/storage/` per `/docs/attachments.md`):
  - the dispatch wave `.md` file — names the package TSV and the lane TSV for that wave;
  - the package TSV — one row per package: item to move, source store, destination store, delivery due time, and the margin earned if it arrives;
  - the lane TSV — one row per directed transport link: origin, destination, capacity per trip, ETA, trip cost, and `delay_hint`.
- `/docs/dispatch.md` — the authoritative dispatch-planning policy.
- Tools: `/bin/cat` to read the wave/TSV files (`ws.read`); `execute_python` to parse TSVs and compute the plan. `/bin/sql` is unavailable and is not needed here — the wave inputs are the source of truth.

## Process

From `/docs/dispatch.md`:

1. Read the wave `.md` file first; it names the package TSV and lane TSV. Read both.
2. Parse package rows (item, `from_store_id`, `to_store_id`, due time, margin) and lane rows (origin, destination, capacity per trip, ETA, trip cost, `delay_hint`). The `delay_hint` summarizes past delay observations.
3. Build one assignment per package. A **route** is an ordered list of lane ids that starts at the package `from_store_id` and ends at `to_store_id`; it may be a direct lane or multiple hub lanes, but **every consecutive lane must connect** (each lane's destination is the next lane's origin).
4. Assign a **priority** per assignment. Lower priority numbers load first within each lane queue — use priorities to decide which packages get scarce early capacity when several assignments share a lane.
5. **Maximize expected net profit**, not just the number of delivered packages. Weigh each package's margin against trip costs along its route and the expected penalty: "late and missed packages incur penalty: per delay time, and per missed package." Use `delay_hint` and ETA against the due time to estimate expected delay/miss.
6. Return **only one JSON object** with one assignment per package, in the shape from `/docs/dispatch.md`:

   ```json
   {
     "assignments": [
       {"package_id": "<id>", "route": ["<lane>", "<lane>"], "priority": 1}
     ]
   }
   ```

   Emit exactly this object as the answer (no surrounding prose), per [submission_terminal](submission_terminal.md).

## Outcomes

- `OUTCOME_OK`: a valid `assignments` JSON object is produced — one assignment per package, every route connected from `from_store_id` to `to_store_id`, priorities set, expected net profit maximized.
- `OUTCOME_NONE_CLARIFICATION`: the wave file or a named TSV is missing/unreadable, or the request does not point to a wave `.md` file.
- `OUTCOME_NONE_UNSUPPORTED`: the request asks for a dispatch action the planning policy and inputs do not support (e.g. mutating a commerce record).

## Refs to set in scratchpad

- The request-named input artifacts the plan is derived from: the wave `.md` file, the package TSV, and the lane TSV (their absolute live paths, e.g. under `/storage/`). These are class-1 input artifacts — see [refs](refs.md).
- `/docs/dispatch.md` — the applied planning policy.
- Do not cite commerce `/proc/...` records unless the wave inputs reference them and the answer is derived from them.

## Anti-patterns

- Returning more than one JSON object, or wrapping the object in prose. `/docs/dispatch.md`: "Return only one JSON object with one assignment per package."
- Building a route whose consecutive lanes do not connect, or that does not start at `from_store_id` / end at `to_store_id`.
- Optimizing for delivered-package count instead of expected net profit; ignoring trip cost, `delay_hint`, ETA, due time, and the late/missed penalties.
- Ignoring shared-lane capacity when setting priorities (lower number loads first).
- Citing only downstream `/proc` records while omitting the wave/TSV input artifacts the plan was derived from.
- Mutating commerce records — dispatch planning is a plan output, not a commerce action.

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived.

- `/docs/dispatch.md` — the wave-file → package/lane TSV flow, route connectivity rule, priority semantics, the maximize-expected-net-profit objective, the late/missed penalty rule, and the required output JSON shape.
- `/docs/attachments.md` — defines `/storage` as the input-artifact root for the wave/TSV files.
- `bin-help/cat.help.txt` — the file read tool for the wave and TSV inputs.
