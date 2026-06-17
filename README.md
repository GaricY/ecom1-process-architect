# ecom1-process-architect

An autonomous agent for the **BITGN Agent Challenge: E-commerce (ECOM1)**. It
connects to the BitGN API and solves digital-store tasks inside a deterministic
simulation — product discovery, cart/checkout, payment failures, fraud
boundaries, returns, refunds, replacements, support — and is graded on
**observable actions, state changes, and policy compliance**, not on prose.

## The idea

I spent 15+ years implementing ERP systems, and every project starts the same
way. Where do you begin? ~~You sit down and write code.~~ You **map the business
processes.** The code comes later; it is only one way to express a process that
already exists — in the policy book, in people's heads, in how the business
actually runs.

This agent is built on that instinct: the business-process map comes first, as a
first-class artifact — and then it gets the discipline you would apply to a
codebase. Because designing business processes and writing software have a lot in
common: both turn messy real-world requirements into precise, composable, testable
rules, and both rot when they grow as one ever-expanding blob nobody dares touch.

So the core bet is simple: **treat the agent's operating instructions as code,
and apply software engineering to them.**

And a second bet that follows from it: **don't hard-code the domain into the
machinery — let the agent build it.** The orchestrator, the resolver, the
versioned store, the PA loop — none of it knows anything about e-commerce. All
the domain knowledge lives in the business-process units, which the agent derives
from the live world itself (`world_create` / `world_refresh`). Point the same
machine at a different world and it maps a new process set — the domain is the
agent's job, not the framework's.

What that means concretely:

- **Instructions are modular, versioned, immutable units.** The Executor's
  operating manual is not one giant prompt but a set of business-process (BP)
  units — identity & auth, checkout, discounts, fraud review, returns, refs
  hygiene, … — each an immutable `vNNNN/` with its own content, manifest, and
  **declared dependencies** on the world (specific docs, tool `--help`, DB
  schema). It reads like a small codebase, not a wall of text.
- **The "world" is the upstream those units depend on.** The organizer's docs,
  tools, and policies are the dependency surface. When they drift, the units that
  pinned them go *stale* — exactly like a dependency bump that breaks a module —
  and a resolver picks, per task, the version whose dependencies still match the
  live world.
- **The Process Architect (PA) is the engineer in the loop.** It ships new
  versions from feedback the way a developer responds to CI:
  - a failing trial (the grader's score) → `failure_fix`: fix the unit behind the
    failure — a bug fix driven by a failing test;
  - the world drifted → `world_refresh`: an incremental refactor of the affected
    BPs (or `refresh` for a single stale unit);
  - a brand-new or radically different world (e.g. `dev → prod`) → `world_create`:
    a greenfield rebuild of the whole BP set from the current world dump. The
    initial BP set was bootstrapped exactly this way.
- **Everything is auditable history.** Immutable `vNNNN/` with diffs and change
  notes, a baseline snapshot of "the world as we last accepted it", and a
  registry of active units — a git-like trail for the agent's own instructions.

The payoff: instead of one static prompt that nobody can safely change, the
agent carries a modular, version-controlled, self-evolving operating manual —
and it adapts to a changing benchmark the way well-engineered software adapts to
changing requirements.

## How it works

- **Executor** — runs as `claude -p` inside a per-trial directory; its only
  runtime tool is the MCP server `mcp__ecom-python__execute_python` (it writes
  Python snippets that execute in the task VM and finish with
  `submit_and_exit(...)`). Its prompt (`CLAUDE.md` + `business_processes/*.md`)
  is **rendered per trial by the resolver** from the versioned store
  `instructions/units/<id>/vNNNN/` — never a hand-maintained static file.
- **Process Architect (PA)** — between trials, evolves the instruction units by
  emitting a new immutable `vNNNN/`. Modes:
  - `failure_fix` / `fix_blind` — once a trial score (or, under blind eval, the
    Executor trace) is available, analyse each failure and fix the offending
    unit(s).
  - `world_refresh` — when foundational world files drift vs the latest baseline,
    **incrementally** refresh existing BPs, add new ones for new domains, and
    advance the baseline.
  - `world_create` — same drift trigger, but **rebuilds the whole BP set** from
    the current world dump (existing units are only drafts / naming anchors).
    For a brand-new or radically different world — and how the initial BP set was
    bootstrapped.
  - `refresh` — a single unit whose per-unit dependency drifted.

  All PA **content modes are off by default** (see [Configuration](#configuration)):
  the mechanism stays on so drift still surfaces to the Executor, but the agent
  does not rewrite itself unless you ask it to.
- **Orchestrator** — deterministic Python that drives the BitGN harness loop
  (`get_benchmark` → `start_run` → per-trial `start_trial`/`end_trial` →
  `submit_run` → `get_run` for scores), dumps the live world (`/docs`, `/bin`,
  every `AGENTS.md`/`README.md`, tool `--help`, SQL schema) into each trial dir,
  resolves instructions, spawns the Executor and PA, and writes the reports.

## Quickstart

```bash
uv sync                                    # build the venv (uv-managed)
echo 'BITGN_API_KEY=...' > .env            # gitignored
set -a; source .env; set +a

# one task, NOT published to the leaderboard:
CONCURRENCY=1 uv run python -m orchestrator.main t01 --no-submit
# or: make smoke
```

The default benchmark is `bitgn/ecom1-dev` (open, scored). A subset run still
`start_trial`s **every** trial (the harness reveals `task_id` only then) and
**submits to the leaderboard by default** — pass `--no-submit` for a smoke that
should not be published. `make run` runs the whole benchmark; `make task
TASKS="t01 t05"` and `make limit N=5` cover subsets.

## Configuration

Set via environment or the matching CLI flag.

| Variable | Default | Purpose |
| --- | --- | --- |
| `BITGN_API_KEY` | — | Required for `start_run` (anonymous runs need it too). Lives in `.env`. |
| `BITGN_HOST` / `BENCHMARK_HOST` | `https://api.bitgn.com` | Harness URL. |
| `BENCHMARK_ID` / `BENCH_ID` | `bitgn/ecom1-dev` | Benchmark to run (`…-dev` / `…-prod`). |
| `CONCURRENCY` | `1` | Parallel trial workers; also bounds `start_trial` fan-out and bootstrap. |
| `CLAUDE_MODEL` / `--model` | `claude-sonnet-4-6` | Executor model. |
| `CLAUDE_REASONING_EFFORT` / `--effort` | `high` | Executor effort (`low`/`medium`/`high`/`xhigh`/`max`). |
| `CLAUDE_MAX_TURNS` | `40` | Hard turn cap for the Executor. |
| `PA_CLAUDE_MODEL` / `--process-architect-model` | `claude-opus-4-7` | PA model. |
| `PA_CLAUDE_REASONING_EFFORT` / `--process-architect-effort` | `xhigh` | PA effort. |
| `PA_LLM_CONCURRENCY` | `1` | Parallel PA sessions. `0` disables PA entirely (no workdirs; every submit returns `skipped`). |
| `PA_FIX_ENABLED` / `--pa-fix` | `0` | Enable `failure_fix` + `fix_blind`. |
| `REFRESH_ENABLED` / `--refresh` | `0` | Enable per-unit `refresh`. |
| `WORLD_REFRESH_ENABLED` / `--world-refresh` | `0` | Enable `world_refresh`. |
| `WORLD_CREATE_ENABLED` / `--world-create` | `0` | Use `world_create` instead of `world_refresh` for the world-PA pathway (rebuild the whole BP set). |
| `STALE_RESOLUTION` / `--stale-resolution` | `latest_async_refresh` | `latest_async_refresh` — Executor starts on latest, refresh/world_refresh run in background. `wait_for_refresh` — resolver awaits world_refresh first; use for the first run after the world changes. |
| `TRIAL_START_INTERVAL_SEC` | `2` | Minimum seconds between `start_trial` RPCs (spacing happens before the call, so the organizer's timer only counts real work). |
| `BLIND_EMULATION` / `--blind-emulation` | `0` | Emulate the prod blind policy on an open benchmark: the stack sees `score=null`/empty hints; real grader output is kept in a sibling `<run_id>-score/`. |
| `DUMP_SQL_ROWS` / `--dump-sql-rows` | `0` | If `>0`, also dump up to N rows per user table into `dump_sql/`. |
| `RUNS_ROOT` / `--runs-root` | `../../.runs/ecom` | Run-artifacts root (relative to the repo root). Set explicitly to control where runs land. |
| `SMOKE_TASK` | `t01` | Default task id for `make smoke`. |

Submission flags: runs **submit by default**; `--no-submit` leaves the run open
(without `submit_run` the grader does not reveal scores, so `summary.json` stays
`score: null` and `failure_fix` cannot fire). `--no-process-architect` disables
only `failure_fix`/`fix_blind`; `--wait-process-architect` blocks submission on
PA. Full flag list: `uv run python -m orchestrator.main --help`.

## Reading results

After a run, `<RUNS_ROOT>/<run_id>/` contains:

- **`report.md`** — human-readable summary: header aggregates (`wall-clock` /
  `cpu-sum` / `trial-sum` / `boot-sum`) + a per-task table (outcome, score, refs,
  timings). `trial-sum` is the organizer's leaderboard metric (summed
  `start_trial`→`end_trial` wall time).
- **`summary.json`** — the same, machine-readable.
- **`report_PA.md`** — aggregate of PA jobs (when PA ran).
- **`run.json`** — `run_id`, `harness_run_id`, benchmark.

Inside each `NNNN-<task>-<trial>/`:

| Artifact | What it shows |
| --- | --- |
| `task.md` | The task text (randomized per run by the organizer). |
| `CLAUDE.md`, `business_processes/` | The prompt the Executor actually saw (rendered by the resolver). |
| `vault/`, `bin-help/`, `tree.md` | The live world dump for the task (docs, tools, DB schema). |
| `attention/` | World delta vs baseline (drift + relocations) shown to the Executor. |
| `answer.json`, `result.json` | Final answer (outcome, refs) and trial outcome (score, timings, turns, MCP calls). |
| `.logs/transcript.jsonl` | Full Executor stream-json transcript. |
| `.logs/mcp-tool-calls.jsonl`, `.logs/python/` | Every `execute_python` call and snippet — the core of "what the agent did". |
| `.logs/instruction-selection.json` | Which unit versions the resolver chose + the world-drift it saw (the stable per-run "snapshot"). |

To compare two runs, diff the **resolver selection + world-drift** in
`instruction-selection.json`, not `task.md` — the task text is randomized
per run.

**Example runs.** `runs/` ships archived `ecom1-dev` runs you can explore offline:

- `20260530-050756` — a full 53-trial run (the dev-training endpoint).
- `20260521-123446` — a run where `failure_fix` PA **drifts four different
  processes in one pass**: from four failing trials it fixed `identity_and_auth`,
  `discount`, `payments_3ds_recovery`, and `refs_and_submission`. Open the
  `*-process-architect/pa-output/` workdirs to see each fix, its rationale, and
  the new unit version it produced.

Unpack one with `tar xzf runs/<id>.tar.gz` and browse the artifacts described
above.

## Repository layout

```
pyproject.toml / Makefile / uv.lock   # uv-managed build + run aliases
orchestrator/                         # deterministic Python (harness loop, resolver, PA)
instructions/                         # versioned source of truth
  registry.json                       #   flat unit roster
  world.json, world_baseline/vNNNN/   #   foundational "world map" + immutable baselines
  units/<id>/vNNNN/                   #   immutable per-unit versions (content + manifest + deps)
  prompts/process_architect/          #   PA prompts (failure_fix / refresh / world_refresh / world_create / conflict)
static-instructions/                  # runtime statics copied verbatim (runtime_prelude.py, workspace.py, .claude/)
runs/                                 # archived example runs (tar.gz) — see "Reading results"
```

<details><summary>Detailed code map (orchestrator/)</summary>

```
orchestrator/
  main.py               # CLI + harness loop + run wiring
  config.py             # env-driven config
  harness.py            # BitGN harness helpers
  bootstrap.py          # PreBootstrapDumper + BinHelpBootstrapper (world dump)
  task_dir.py           # per-trial materialisation
  claude_runner.py      # spawn `claude -p`, stream-json transcript
  mcp_python_server.py  # stdio MCP server with execute_python
  python_executor.py    # snippet runner
  session_registry.py   # opaque session id ↔ harness_url
  report.py             # summary.json + report.md
  sql_schema.py         # generator for bin-help/sqlite_schema.txt
  bp_admin.py           # human-only CLI: retire / rollback / world-baseline
  instructions/
    store.py            #   registry, manifest, version walking
    fingerprints.py     #   sha256 index across vault/ + bin-help/ + static/
    world_baseline.py   #   world layer (load + drift + baseline write)
    resolver.py         #   match-or-fallback + render task_dir
    versioning.py       #   atomic vNNNN/ writer + registry append
    pa_decision.py      #   decision validators + apply
    pa_queue.py         #   priority queue + per-unit / registry locks
    pa_runner.py        #   spawn PA Claude CLI + post-run artifacts
    pa_workdir.py       #   per-mode workdir materialisers + ingest
```

</details>

New run artifacts are written **outside** the repo, under `RUNS_ROOT`; the
committed `runs/` here only holds example archives.
