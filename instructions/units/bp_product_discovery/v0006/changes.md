# bp_product_discovery v0006

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-05-21T01:31:22+00:00`
- parent: `v0002`

## Rationale

On an availability question (`how many of these N products have at least K available at store S`) the Executor copied every candidate product's `products.path` into `refs`, including SKUs whose `available_today` was `0` or `NULL` (i.e. unavailable today at that store). The grader rejected the trial with `answer contains invalid reference '/proc/catalog/.../HND-<sku>.json'` on the `available_today=0` SKU. The existing v0002 already quotes the `/AGENTS.MD` rule that availability answers must reference only what is available, but it scoped that rule to the answer message; this edit makes the rule explicit for `refs` too. New step 6 classifies each candidate by the question's availability test and requires `products.path` to be copied into `refs` only when that test passed; the `Refs to set in scratchpad` section gains a matching bullet, and a new anti-pattern names the exact grader error so future Executors recognise it. Step 2 also clarifies that both `NULL` (no inventory row) and `0` count as not-available so the classification is unambiguous. `/AGENTS.MD` is added to inputs and dependencies because the rule is now load-bearing for `refs`, not just message wording.

## Rollback

Create a new version from v0002 content if the stricter refs-shaping rule causes Executors to under-cite catalogue paths on edge-case availability questions (e.g. a question that explicitly asks the Executor to enumerate all considered products).

## Dependencies
- `workspace:/docs/README.md` — Source of the catalogue reporting rule and the dated-update folder list used by step 3 of the BP.
- `workspace:/AGENTS.MD` — Source of the reply-shaping rule 'availability answers reference only what is available'. Step 6 and the new refs/anti-pattern bullets extend this rule from the answer message to refs, so the BP becomes stale if the rule wording moves or changes.
- `bin_help:sql.help.txt` — Defines the products / inventory / stores table shapes (including `inventory.available_today` and the LEFT JOIN semantics) that the availability classification in step 2 and step 6 relies on.
- `bin_help:date.help.txt` — Step 3 still makes /bin/date the only trusted source for the operating-day comparison on dated updates; the BP is wrong if /bin/date's contract changes.
- `bin_help:id.help.txt` — Step 1 calls /bin/id at session start; the BP's actor handling depends on its output shape.
