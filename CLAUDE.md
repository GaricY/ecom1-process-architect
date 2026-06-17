# CLAUDE.md — operating this repo

Working notes for whoever drives this repo (a Claude Code session or a developer):
how to run trials, how to read the artifacts, and what not to break. For the
concept, the architecture, and the **full env/CLI reference**, see
[README.md](README.md) — this file does not repeat them.

The two LLMs inside a run are the **Executor** (`claude -p` solving one trial via
`execute_python`) and the **Process Architect / PA** (evolves the instruction
units between trials). **You are neither** — you edit orchestrator code and PA
prompts, launch runs, and analyse the results.

## Source of truth — what you may and may not edit

- `instructions/units/<id>/vNNNN/` — **immutable** versioned source of truth for
  the Executor prompt (`executor_core`) and the business processes. Never
  hand-edit an existing version; a content fix is a new version
  (`orchestrator.bp_admin rollback` makes one from old text).
- `static-instructions/` — runtime statics the resolver copies into each
  task_dir verbatim: `runtime_prelude.py`, `workspace.py`, `.claude/settings.json`,
  `business_processes/CLAUDE.md`. Substantive prompts/BPs do **not** live here.
- `instructions/prompts/process_architect/*.md` — PA prompts (`failure_fix`,
  `fix_blind`, `refresh`, `world_refresh`, `world_create`, `conflict` + their
  `*_user.md` and `bp_author_contract.md`). **Not versioned** — editing them
  affects future PA runs but does not invalidate already-released unit versions.
- `instructions/registry.json` (unit roster), `instructions/world.json` +
  `world_baseline/vNNNN/` (the world layer the resolver diffs against).
- `orchestrator/` — deterministic Python (harness loop, resolver, PA queue).

## Running — recipes

Prereqs: `uv sync`, and `.env` holding `BITGN_API_KEY`. Then
`set -a; source .env; set +a`. Defaults: Executor `claude-sonnet-4-6` / `high`,
PA `claude-opus-4-7` / `xhigh`. Positional args (`t01`, …) are a substring
filter on `task_id`.

- **Clean observation run** (no self-edits — the usual case; all PA content modes
  are off by default):
  ```bash
  CONCURRENCY=1 uv run python -m orchestrator.main t01 --no-submit
  ```
  Add `PA_LLM_CONCURRENCY=0` to also skip materialising PA workdirs entirely.
- **Training run** (let PA evolve the units): enable the relevant gate(s) —
  `--pa-fix` (score → `failure_fix`), `--refresh`, `--world-refresh`. A full
  benchmark run submits by default, which is what reveals the scores `failure_fix`
  needs.
- **Prod / a changed world**: `--world-refresh` (incremental) or `--world-create`
  (rebuild the whole BP set — for a brand-new/very different world). For the first
  run after the world changed, add `--stale-resolution wait_for_refresh` so the
  trial gets freshly-refreshed BPs instead of a stale fallback.
- **Blind emulation** (dry-run the prod blind policy on dev): `--blind-emulation`
  — the stack sees no scores; the real grader output is kept in a sibling
  `<run_id>-score/`.

Notes:
- A subset run still `start_trial`s every trial and **submits by default** — keep
  `--no-submit` for anything that should not hit the leaderboard.
- **Flat layout caveat:** the default `RUNS_ROOT` (`../../.runs/ecom`) resolves
  *above* the repo root. Set `RUNS_ROOT` explicitly when you care where runs land.
- Full env/flag list: README → Configuration, or `… orchestrator.main --help`.

## Analysing a run

Run dir `<RUNS_ROOT>/<run_id>/`: `report.md` (human), `summary.json` (machine),
`report_PA.md` (PA jobs), `run.json` (ids + benchmark).

Per `NNNN-<task>-<trial>/`, the useful artifacts:

- `CLAUDE.md` + `business_processes/` — exactly what the Executor saw (resolved).
- `vault/` + `bin-help/` + `tree.md` — the live world dump for the task.
- `attention/` — world drift + relocations vs baseline shown to the Executor.
- `result.json` / `answer.json` — outcome, score, refs, timings, turns, MCP calls.
- `.logs/python/` + `.logs/mcp-tool-calls.jsonl` — every `execute_python` call;
  the first stop for "what did the agent actually do".
- `.logs/transcript.jsonl` — full Executor transcript.
- `.logs/instruction-selection.json` — resolver choice (units/versions) +
  `world_drift`. This is the **stable per-run snapshot**: to compare two runs,
  diff this, **not** `task.md` (task text is randomized per run).

An archived example run ships in `runs/` (`tar xzf runs/20260530-050756.tar.gz`).

## Conventions / gotchas

- `instructions/units/<id>/vNNNN/` is immutable — never edit in place.
- Don't commit `.env` (gitignored) or run artifacts.
- PA content modes are **off by default**, each gated independently
  (`--pa-fix` / `--refresh` / `--world-refresh` / `--world-create`);
  `PA_LLM_CONCURRENCY=0` is the full kill-switch.
- `orchestrator.bp_admin` (retire / rollback / world-baseline) is **human-only** —
  PA never calls it, and you rarely need it in normal operation.
