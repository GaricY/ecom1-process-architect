# Process Architect: Operations

Runbook for launching BitGN ECOM1 and preparing the environment for a dev-to-prod transition. This document defines the baseline operating procedures.

Main entry point:

```bash
uv run python -m orchestrator.main [task-filter ...] [flags]
```

Initial setup before the first run:

```bash
uv sync
export BITGN_API_KEY=...
```

## 1. Branch Management

* To work in the dev environment: switch to the `postmortem-dev` branch.
* For the dev-to-prod transition (via `world_refresh`): use the `postmortem-dev` branch and see the "Dev-to-Prod" section of this document.
* To evaluate the final prod state: switch to the `postmortem-prod` branch.

```bash
git switch postmortem-dev
git switch postmortem-prod
```

## 2. System Requirements

* Python version `>=3.14` and the `uv` package manager.
* Claude Code CLI: the `claude` executable must be available in `PATH` or explicitly set through `CLAUDE_BIN=/path/to/claude`.
* Claude CLI must already be authorized in the user's working environment.
* BitGN API access: network reachability to the harness and a `BITGN_API_KEY` token.
* The target benchmark for the dev/prod environment must be set through `--benchmark`.

## 3. Running

Standard dev run on the `postmortem-dev` branch:

```bash
uv run python -m orchestrator.main \
  --benchmark bitgn/ecom1-dev \
  --concurrency 1
```

Run selected dev tasks:

```bash
uv run python -m orchestrator.main t01 t05 \
  --benchmark bitgn/ecom1-dev \
  --concurrency 1
```

Full prod run on the `postmortem-prod` branch:

```bash
uv run python -m orchestrator.main \
  --benchmark bitgn/ecom1-prod \
  --concurrency 15 \
  --pa-llm-concurrency 0
```

Advanced PA (Process Architect) modes are disabled by default: `--pa-fix`, `--refresh`, `--world-refresh`, and `--world-create` require explicit activation. The default `--pa-llm-concurrency 1` only defines PA queue capacity; if the modes above are not active, PA does not change processes. To disable PA completely, use `--pa-llm-concurrency 0`.

Enable PA-fix mode (evolution) after failed trials:

```bash
uv run python -m orchestrator.main \
  --benchmark bitgn/ecom1-dev \
  --concurrency 1 \
  --pa-fix
```

Positional `task-filter` arguments are applied as substring filters over `task_id`. Because the harness reveals `task_id` only after `start_trial` initialization, irrelevant trials are still started and then closed with `OUTCOME_ERR_INTERNAL`.

## 4. Dev-to-Prod Transition

The goal of the transition is to adapt processes to the prod runtime without using prod tasks and their results as training data. The prepared prod executor profile is located in `.tasks/task-005/executor_core_prod/v0018/`.

1. Copy the prod `executor_core` configuration if it is missing in the current branch.

```bash
test -d instructions/units/executor_core/v0018 || \
  cp -a .tasks/task-005/executor_core_prod/v0018 \
    instructions/units/executor_core/v0018
```

2. Start a carrier run that executes `world_refresh`.

```bash
BITGN_API_KEY=... \
uv run python -m orchestrator.main t001 \
  --benchmark bitgn/ecom1-prod \
  --concurrency 1 \
  --pa-llm-concurrency 1 \
  --world-refresh \
  --stale-resolution wait_for_refresh
```

## 5. Main Parameters

CLI flags take precedence over environment variables and defaults defined in `orchestrator/config.py`.

Execution / Executor parameters:

| Variable / Flag | Default | Description |
| --- | --- | --- |
| `BITGN_API_KEY` / `--bitgn-api-key` | empty | API key for initializing `start_run`. |
| `BENCHMARK_ID`, `BENCH_ID` / `--benchmark` | `bitgn/ecom1-dev` | Benchmark identifier, usually `bitgn/ecom1-dev` or `bitgn/ecom1-prod`. |
| `RUN_NAME` / `--run-name` | `@GaricY Process Architect postmortem` | Run name in the harness and generated reports. |
| `RUNS_ROOT` / `--runs-root` | `../.runs/ecom` | Root directory for local run artifacts. |
| `CONCURRENCY` / `--concurrency` | `1` | Number of parallel trial worker processes. |
| `CLAUDE_BIN` / `--claude-bin` | `claude` | Path to the Claude CLI executable. |
| `CLAUDE_MODEL` / `--model` | `claude-sonnet-4-6` | Model used by Executor. |
| `CLAUDE_REASONING_EFFORT` / `--effort` | `medium` | Executor reasoning detail level: `low`, `medium`, `high`, `xhigh`, `max`. |
| `CLAUDE_MAX_TURNS` / `--max-turns` | `40` | Maximum number of Executor iterations (turns). |

Process Architect (PA) parameters:

| Variable / Flag | Default | Description |
| --- | --- | --- |
| `PA_LLM_CONCURRENCY` / `--pa-llm-concurrency` | `1` | Number of parallel PA LLM jobs; `0` disables PA completely. |
| `PA_FIX_ENABLED` / `--pa-fix`, `--no-pa-fix` | `false` | Allows `failure_fix` / `fix_blind` after a failed trial. |
| `REFRESH_ENABLED` / `--refresh`, `--no-refresh` | `false` | Allows per-unit refresh when dependency drift occurs. |
| `WORLD_REFRESH_ENABLED` / `--world-refresh`, `--no-world-refresh` | `false` | Allows world-level refresh based on the drift baseline. |
| `WORLD_CREATE_ENABLED` / `--world-create`, `--no-world-create` | `false` | Starts `world_create` instead of `world_refresh` to create a new world baseline from the current dump or handle strong drift. |
| `STALE_RESOLUTION` / `--stale-resolution` | `latest_async_refresh` | Action when stale dependencies are detected: `latest_async_refresh` or `wait_for_refresh`. |
| `PA_APPLY` / `--pa-apply`, `--no-pa-apply` | `true` | Applies valid PA decisions; `--no-pa-apply` switches to dry-run mode without applying changes. |
| `PA_CLAUDE_MODEL` / `--process-architect-model` | `claude-opus-4-8` | Model used by PA. |
| `PA_CLAUDE_REASONING_EFFORT` / `--process-architect-effort` | `xhigh` | PA reasoning detail level. |

## 6. Additional Parameters

Additional execution / Executor settings:

| Variable / Flag | Default | Description |
| --- | --- | --- |
| `BITGN_HOST`, `BENCHMARK_HOST` / `--host` | `https://api.bitgn.com` | Network address of the BitGN harness. |
| `--no-submit` | off | Leaves the run open after trials complete; scores are not revealed until the run is submitted. |
| `--limit` | empty | Limits execution to the first N trials from the selected benchmark. |
| `TRIAL_START_INTERVAL_SEC` / `--trial-start-interval` | `2` | Interval in seconds between `start_trial` initialization; `0` disables the delay. |
| `--trial-timeout` | `1800` | Total Claude CLI session timeout for one trial, in seconds. |
| `--snippet-timeout` | `180` | Timeout for one `execute_python` snippet, in seconds. |
| `--internal-error-retries` | `5` | Number of Executor retry attempts when `answer.json` is missing or `OUTCOME_ERR_INTERNAL` occurs. |
| `DUMP_SQL_ROWS` / `--dump-sql-rows` | `0` | Row limit for dumping user tables into `dump_sql/`; `0` disables the dump. |
| `BLIND_EMULATION` / `--blind-emulation`, `--no-blind-emulation` | `false` | DEV emulation of the blind policy: scores and hints are hidden from the agent stack, while actual scores are written to `<run_id>-score/`. |

Additional PA settings:

| Variable / Flag | Default | Description |
| --- | --- | --- |
| `PA_MAX_TURNS` / `--process-architect-max-turns` | `0` | Maximum number of PA turns; `0` means no `--max-turns` is passed and only the timeout applies. |
| `PROCESS_ARCHITECT_TIMEOUT_SEC` / `--process-architect-timeout` | `1200` | Timeout for non-world PA modes: `refresh`, `failure_fix`, `fix_blind`, conflict retry. |
| `PROCESS_ARCHITECT_WORLD_TIMEOUT_SEC` / `--process-architect-world-timeout` | `7200` | Timeout for `world_refresh` / `world_create` modes. |
| `PA_CONFLICT_MODE` / `--pa-conflict-mode`, `--no-pa-conflict-mode` | `true` | Rebases a PA decision when its base version is stale at apply time. |
| `PA_CONFLICT_MAX_RETRIES` / `--pa-conflict-max-retries` | `1` | Maximum number of conflict rebase attempts. |
| `--process-architect`, `--no-process-architect` | enabled | Legacy gate that activates only PA-fix modes; it does not enable `refresh` or `world_refresh`. |
| `--wait-process-architect` | off | Blocks run continuation until PA failure-fix completes; used only in exceptional cases. |

## 7. `task_dir` Structure

Each trial gets an isolated directory with the following pattern:

```text
<RUNS_ROOT>/<run_id>/<NNNN>-<task_id>-<trial_id>/
```

Key files and directories:

| Path | Purpose |
| --- | --- |
| `task.md` | Task text and base instruction for Executor. |
| `CLAUDE.md` | Compiled `executor_core` version. |
| `business_processes/*.md` | Compiled business process versions. |
| `vault/` | Dump of current `/docs`, `/bin`, `AGENTS.MD`, `README.md`, and related resources. |
| `bin-help/` | Help output (`--help`) for utilities in `/bin/*` and the `sqlite_schema.txt` file. |
| `tree.md` | Snapshot of the VM file tree at trial start. |
| `attention/` | Drift data, relocation maps, and warnings for stale dependencies. |
| `scratchpad.json` | Intermediate Executor scratchpad file. |
| `state.json` | Working state preserved between `execute_python` snippet executions. |
| `answer.json` | Final system answer: `message`, `outcome`, `refs`. |
| `result.json` | Execution data: outcome, score, turns, cost, timings, MCP calls. |
| `runtime_prelude.py` | Helper runtime code available to snippets. |
| `dump_sql/` | SQL dump, generated when `--dump-sql-rows > 0`. |
| `.logs/transcript.jsonl` | Streaming JSON transcript of the Claude CLI run. |
| `.logs/claude-stderr.log` | Claude CLI stderr log, if present. |
| `.logs/mcp-tool-calls.jsonl` | Full log of MCP calls initiated by Executor. |
| `.logs/python/` | Log of `execute_python` snippet execution and results. |
| `.logs/executor_actions.md` | Human-readable Executor action audit. |
| `.logs/instruction-selection.json` | Log of unit version selection by Resolver and captured drift. |
| `.logs/pre-bootstrap-manifest.json` | Manifest of files copied into `vault/` and their processing rules. |
| `.logs/bin-help-manifest.json` | Checksums and contents of `bin-help/`. |

For run analytics and comparisons, prefer `.logs/instruction-selection.json` over `task.md`, because BitGN may randomize task text across different runs.

## 8. Run Artifacts

The following artifacts are generated in the run root directory:

| Path | Purpose |
| --- | --- |
| `run.json` | Local `run_id`, harness `harness_run_id`, benchmark, trial identifiers. Written immediately after `start_run`. |
| `console.log` | Full dump of orchestrator stdout/stderr. |
| `summary.json` | Final execution results in machine-readable format. |
| `report.md` | Detailed analysis report: score, outcome, costs, timings. |
| `report_PA.md` | Aggregated PA task report, generated if PA was run. |
| `<task_dir>/...` | Artifacts for individual trial executions. |
| `<task_dir>-process-architect*/` | Working directories for PA tasks. |

Key metrics in `report.md`:

| Field | Meaning |
| --- | --- |
| `wall-clock` | Actual total run duration. |
| `cpu-sum` | Total Executor runtime across all trials. |
| `trial-sum` | Total time from `start_trial` to `end_trial`, approximately matching the organizer metric. |
| `boot-sum` | Time spent preparing `task_dir`. |
| `executor: turns/mcp/cost` | Resources spent by Executor. |
| `process architect: jobs/turns/cost` | Resources spent by PA. |

When blind emulation is enabled, a parallel `<run_id>-score/` directory is created with actual scores for manual analysis. The main execution process keeps its original blind-shaped configuration.
