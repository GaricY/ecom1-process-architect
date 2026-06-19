# Plan: prepare the dev -> prod postmortem branch

## Context

This branch is meant to be the starting point for postmortem experiments. The
orchestrator should remain usable on dev, while also surviving the prod runtime
where normal SQL is unavailable and the data surface is exposed through live
JSON records under `/proc` plus runtime tools.

The goal is not full automation and not training on prod tasks. The goal is a
clean counterfactual: how well the agent would have scored if only the
runtime/tooling mistakes found in postmortem had been fixed before the run.

Constraints:

- do not inspect the prod task set or change processes based on prod run
  results;
- do not add task-specific prompts, expected answers, or prod entity hints;
- `world_refresh` may run once as world adaptation, not as a solution to
  specific tasks;
- keep the prod `executor_core` as a prepared prompt artifact under
  `.tasks/task-005/executor_core_prod/`, not as an active dev process version.

## Preparation commit scope

1. Orchestrator fallback for the prod data surface.

   When `/bin/sql` cannot return a usable schema, bootstrap should reconstruct
   the agent-facing `bin-help/sqlite_schema.txt` from live `/proc` JSON records.
   This does not make SQL available. It gives the agent a structure map of the
   world and a clear signal that data must be read via `/proc`/JSON rather than
   SQL.

2. Prepared prod `executor_core` prompt.

   The prompt lives in `.tasks/task-005/executor_core_prod/v0018/` as an artifact
   that can be manually enabled for a prod experiment. On this starting dev
   branch it must not become an active `instructions/units/executor_core`
   version.

3. Publication runbook.

   README should include a short explanation of:

   - why the `/proc` fallback exists;
   - why this is a runtime/tooling fix, not prod-task training;
   - how to prepare `executor_core` for prod;
   - how to freeze process state after `world_refresh` before evaluation.

## Runtime fallback

Bootstrap behavior:

- first try the normal `/bin/sql` + `sqlite_schema` path;
- if SQL transport, exit status, or schema content is unusable, read `/proc`;
- sample JSON records across families;
- build a structure-only schema document with `orchestrator/proc_schema.py`;
- write that document to `bin-help/sqlite_schema.txt`.

Expected recovered-schema header:

```text
# Warehouse schema — reconstructed from the live /proc projection.
```

Meaning of this file:

- it is not SQL DDL;
- it is a map of available JSON records;
- it tells the executor prompt that SQL is unavailable and `/proc` is the source
  of truth;
- it is a world-tracked artifact, so `world_refresh` sees the drift in
  `bin-help/sqlite_schema.txt`.

Dev must keep working: if SQL returns a normal schema, bootstrap keeps the old
behavior.

## Prod executor prompt artifact

The prompt in `.tasks/task-005/executor_core_prod/v0018/` should describe only a
generic degraded-runtime contract:

- if `bin-help/sqlite_schema.txt` starts with the recovered `/proc` header,
  treat SQL as unavailable;
- do not spend turns probing known-broken SQL;
- read data with `ws.list("/proc")`, `ws.find(...)`, `ws.read(...)`, and Python
  `json.loads`;
- perform runtime mutations and final submit only through the normal runtime
  tools / `execute_python`;
- do not add concrete prod families, product names, task classes, expected
  answers, or hints learned from runs.

This prompt is not an active process on the dev branch. Before a prod experiment
it can be manually published as a new `executor_core` version if the experiment
is meant to evaluate the postmortem-fixed executor without further training.

## Prod runbook after world_refresh

1. Start from a clean branch state.

   The live instruction store should not contain prior prod run results, PA-fix
   results, or old active BP versions that the resolver can select instead of
   the refreshed ones.

2. Manually enable the prod `executor_core` if the experiment requires this
   prompt.

   Prompt source: `.tasks/task-005/executor_core_prod/v0018/`.

3. Run exactly one `world_refresh` carrier.

   Use one prod task such as `t001`, `--submit`, and
   `--stale-resolution wait_for_refresh`. This run is only a carrier for the
   live world dump. Its score must not be used to edit processes.

   Example shape:

   ```bash
   BITGN_API_KEY=... \
   uv run python -m orchestrator.main t001 \
     --benchmark bitgn/ecom1-prod \
     --concurrency 1 \
     --pa-llm-concurrency 1 \
     --world-refresh \
     --stale-resolution wait_for_refresh \
     --no-refresh \
     --no-pa-fix \
     --submit \
     --trial-timeout 1800
   ```

4. Freeze process state after a successful `world_refresh`.

   Mark all old BP versions that should not participate in evaluation as
   stale/retired, but keep the files in place. Future PA-fix runs should still
   see history, while the resolver in a clean competition run must not fall back
   to old active versions.

   Practical rule:

   - latest refreshed BP versions remain `active`;
   - older BP versions get status `retired` or an equivalent stale marker;
   - handle `executor_core` separately and do not change it here;
   - do not archive or delete history.

5. Before full runs, execute a short prod subset.

   Run with PA disabled:

   ```bash
   BITGN_API_KEY=... \
   uv run python -m orchestrator.main t001 t002 t003 \
     --benchmark bitgn/ecom1-prod \
     --concurrency 3 \
     --pa-llm-concurrency 0 \
     --no-world-refresh \
     --no-refresh \
     --no-pa-fix \
     --submit \
     --trial-timeout 1800
   ```

   Check only orchestration-state cleanliness:

   - `.logs/instruction-selection.json` selects only active latest versions;
   - retired/stale historical BP versions are not selected;
   - PA jobs = 0;
   - stale/world-drift attention matches the expected baseline state and does
     not hide fallback to old processes.

   If selection pulls old versions, do not continue to a full run. Return to a
   clean starting state, fix the cause, and repeat `world_refresh`.

6. Run full prod submissions.

   For autonomous runs use concurrency `15`: `35` already hit rate limits.
   Individual prod tasks may run for 15-20 minutes; that alone is not a reason
   to kill the process.

   ```bash
   BITGN_API_KEY=... \
   uv run python -m orchestrator.main \
     --benchmark bitgn/ecom1-prod \
     --concurrency 15 \
     --pa-llm-concurrency 0 \
     --no-world-refresh \
     --no-refresh \
     --no-pa-fix \
     --submit \
     --trial-timeout 1800
   ```

   This is a submitted run, with no attempt to hide the result. During the full
   run, do not run PA-fix, do not change processes based on task failures, and
   do not use current prod-run results as training data.

## Minimal pre-commit checks

- `uv run python -m compileall orchestrator static-instructions`;
- `uv run python -m orchestrator.main --help`;
- synthetic check for `proc_schema.build_recovered_schema_doc()`;
- dev smoke: with working SQL, `bin-help/sqlite_schema.txt` remains a normal SQL
  schema, not a recovered `/proc` document;
- prod smoke/subset: `instruction-selection.json` does not select retired
  versions.

## Excluded from the preparation commit

- full prod run results;
- generated BP versions from a concrete `world_refresh`;
- mass status changes made only for an already completed experiment;
- active `instructions/units/executor_core/v0018`;
- task-specific fixes found from the scoreboard.
