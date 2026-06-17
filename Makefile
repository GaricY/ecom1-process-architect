.PHONY: sync run smoke task limit submit no-submit

SMOKE_TASK ?= t01

sync:
	uv sync

# Smoke: single task, CONCURRENCY=1, defaults (sonnet-4-6 / medium).
smoke:
	CONCURRENCY=1 uv run python -m orchestrator.main $(SMOKE_TASK)

# Run all tasks in the configured benchmark.
run:
	uv run python -m orchestrator.main

# Run a hand-picked subset, e.g. `make task TASKS="t01 t05"`.
task:
	@if [ -z "$(TASKS)" ]; then echo "usage: make task TASKS='t01 t05'"; exit 1; fi
	uv run python -m orchestrator.main $(TASKS)

# Small smoke run (first N tasks).
limit:
	@if [ -z "$(N)" ]; then echo "usage: make limit N=5"; exit 1; fi
	uv run python -m orchestrator.main --limit $(N)

# Explicit submit alias; regular run/smoke/task/limit submit by default too.
submit:
	uv run python -m orchestrator.main --submit

# Run without publishing the run.
no-submit:
	uv run python -m orchestrator.main --no-submit
