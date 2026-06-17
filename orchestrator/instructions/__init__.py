"""Versioned instruction store + deterministic resolver.

Public API:

- `resolve_and_render(...)` — bootstrap-time entry point used by
  `task_dir.materialize`. Picks a matching version per registry unit,
  renders `CLAUDE.md` and `business_processes/*.md` into the task dir,
  writes `.logs/instruction-selection.json`, and (when stale) prepares
  Process Architect refresh artifacts.
- `PaQueue` — long-lived async queue that serialises PA LLM calls under
  `PA_LLM_CONCURRENCY`, with priority tiers + per-unit refresh dedup.
- `queue_failure_fix` / `run_failure_fix` — called from
  `main.run_one_task` after a failed trial. Materialises a failure-fix
  workdir from the selected instruction package + executor artefacts,
  queues a PA job, ingests output into new immutable versions under
  `agent/instructions/units/`.
- `STALE_RESOLUTION_*` constants — config values accepted by the
  orchestrator.

Layout under `agent/instructions/`:

```
registry.json
prompts/process_architect/{common,refresh,failure_fix}.md
units/<unit_id>/v0001/{content.md,manifest.json,changes.md,diff.patch,
                       dependency_snapshot/...}
```
"""

from __future__ import annotations

from .pa_queue import PaJobResult, PaQueue
from .pa_workdir import queue_failure_fix, run_failure_fix
from .resolver import (
    MATCHED,
    MATCHED_AFTER_REFRESH,
    NO_VERSIONS,
    RETIRED_ONLY,
    STALE_LATEST_FALLBACK,
    STALE_REFRESH_FAILED,
    STALE_REFRESH_INCOMPLETE,
    STALE_RESOLUTION_LATEST_ASYNC,
    STALE_RESOLUTION_WAIT,
    VALID_STALE_RESOLUTIONS,
    SelectionResult,
    UnitSelection,
    resolve_and_render,
)
from .store import (
    instructions_dir,
    load_registry,
    pa_prompts_dir,
    preflight_instruction_store,
    units_dir,
)
from .world_baseline import (
    WorldFile,
    effective_world_files,
    load_world_files,
    world_dep_signatures,
)

__all__ = [
    "MATCHED",
    "MATCHED_AFTER_REFRESH",
    "NO_VERSIONS",
    "RETIRED_ONLY",
    "STALE_LATEST_FALLBACK",
    "STALE_REFRESH_FAILED",
    "STALE_REFRESH_INCOMPLETE",
    "STALE_RESOLUTION_LATEST_ASYNC",
    "STALE_RESOLUTION_WAIT",
    "VALID_STALE_RESOLUTIONS",
    "PaJobResult",
    "PaQueue",
    "SelectionResult",
    "UnitSelection",
    "WorldFile",
    "effective_world_files",
    "instructions_dir",
    "load_registry",
    "load_world_files",
    "pa_prompts_dir",
    "queue_failure_fix",
    "preflight_instruction_store",
    "resolve_and_render",
    "run_failure_fix",
    "units_dir",
    "world_dep_signatures",
]
