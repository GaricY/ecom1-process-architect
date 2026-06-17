"""PA LLM job queue — priority + concurrency + per-unit dedup.

One queue lives per orchestrator process. It admits jobs with four
priority tiers and runs at most `PA_LLM_CONCURRENCY` Claude CLI
sessions at once. `PA_LLM_CONCURRENCY=0` is the explicit "PA disabled"
mode: the dispatcher never starts, every `submit_*` returns an already
resolved future with `terminal_status="skipped"`, and the dedup map
caches that skipped future so any late subscriber sees the same
no-op terminal. Callers in `pa_workdir`/`resolver`/`main` should gate
on `pa_queue.disabled` first to skip workdir materialise altogether —
the in-queue gate is defense-in-depth.

- `blocking_refresh`  (0) — wait-mode resolver is blocking a trial on
  this job.
- `world_refresh`     (1) — world-layer drift detected; PA must look at
  the whole picture (new BP units, existing BP refreshes, baseline
  advance). Cheaper than failure_fix to run on async path; runs ahead
  of failure_fix because new BPs shape future trials.
- `failure_fix`       (2) — Executor failed a trial; PA needs to study
  the failure and propose process edits.
- `async_refresh`     (3) — latest-mode resolver started the Executor on
  stale fallback and queued this per-unit refresh for future trials.

Concurrency is enforced by a priority-aware limiter exposed to workers
via the `llm_slot(priority)` async context manager. The worker holds
that slot only around the Claude CLI invocation; deterministic ingest
(decision parsing, version writing, snapshot copying) runs outside the
slot so it never serialises behind LLM time, matching the agreed split.

Dedup is per-run: a `refresh` request for `unit_id=X` returns any
existing future registered for X — running or already complete — so a
later trial can read the cached terminal result rather than re-running
PA. A `world_refresh` request is deduped per `baseline_version` (same
baseline drift => same future). `failure_fix` jobs are not deduped —
each failure carries its own context.

Once a `world_refresh` has been submitted in a run the queue treats the
whole world picture as stale: any subsequent `refresh` / `failure_fix`
submission resolves immediately to `terminal_status="skipped"` with
reason `"world_refresh in this run; stale world makes per-unit PA
pointless"`. The bookkeeping outlives world_refresh completion — even
after the baseline advances, failures from this run happened on the
old world and shouldn't drive new BP versions.

Per-unit write locks live here too so two concurrent jobs that target
overlapping `unit_id`s can never race on `next_version_num`. A global
`registry_write_lock` serialises any mutation to
`agent/instructions/registry.json` (only `world_refresh` mutates it
today).
"""

from __future__ import annotations

import asyncio
import heapq
import itertools
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Awaitable, Callable

PRIORITY_BLOCKING = 0
PRIORITY_WORLD_REFRESH = 1
PRIORITY_FAILURE_FIX = 2
PRIORITY_ASYNC = 3

PRIORITY_LABELS = {
    PRIORITY_BLOCKING: "blocking_refresh",
    PRIORITY_WORLD_REFRESH: "world_refresh",
    PRIORITY_FAILURE_FIX: "failure_fix",
    PRIORITY_ASYNC: "async_refresh",
}


@dataclass
class PaJobResult:
    job_id: str
    kind: str  # "refresh" | "failure_fix" | "fix_blind" | "world_refresh" | "world_create"
    priority: str  # one of PRIORITY_LABELS
    terminal_status: str  # "completed" | "failed" | "rejected" | "timeout" | "dry_run_completed" | "conflict_unresolved"
    duration_ms: int
    pa_dir: str | None = None
    created_versions: list[dict[str, str]] = field(default_factory=list)
    created_units: list[dict[str, str]] = field(default_factory=list)
    new_baseline: str | None = None
    error: str | None = None
    exit_code: int | None = None


# Worker signature: (pa_queue, job_descriptor) -> PaJobResult.
# Returns the terminal result the queue should publish to subscribers.
WorkerCallable = Callable[["PaQueue", "PaJob"], Awaitable[PaJobResult]]


@dataclass
class PaJob:
    job_id: str
    kind: str  # "refresh" | "failure_fix" | "fix_blind" | "world_refresh" | "world_create"
    priority: int
    unit_ids: tuple[str, ...]
    payload: dict[str, Any]
    future: asyncio.Future[PaJobResult]


class PaQueue:
    """Priority-ordered job queue with per-unit refresh dedup.

    A single dispatcher pulls priority-ordered jobs from the queue and
    spawns each as its own asyncio task. Workers then acquire a
    priority-aware LLM slot before the Claude CLI invocation. This keeps
    deterministic ingest outside the LLM cap without letting already
    spawned async-refresh tasks jump ahead of later blocking/failure jobs.
    """

    def __init__(
        self,
        *,
        concurrency: int,
        worker: WorkerCallable,
        refresh_enabled: bool = True,
        world_refresh_enabled: bool = True,
        world_create_enabled: bool = False,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        if concurrency < 0:
            raise ValueError("PA_LLM_CONCURRENCY must be >= 0")
        self._concurrency = concurrency
        self._disabled = concurrency == 0
        # Independent gate for the per-unit `refresh` mode only. When
        # False, `submit_refresh` returns a skipped future WITHOUT
        # touching `_world_refresh_seen` or the dispatcher, so
        # failure_fix / world_refresh keep running normally — unlike
        # `disabled`, which kills the whole PA.
        self._refresh_enabled = refresh_enabled
        # Independent gate for the world_refresh mode only. When False,
        # `submit_world_refresh` returns a skipped future WITHOUT flipping
        # `_world_refresh_seen`, so failure_fix / refresh keep running
        # normally — unlike `disabled`, which kills the whole PA.
        self._world_refresh_enabled = world_refresh_enabled
        # When True, the resolver routes world-PA-drift to `world_create`
        # mode instead of `world_refresh`. Same dedup map, same
        # `_world_refresh_seen` gating — the two modes are mutually
        # exclusive per run (operator opts in via --world-create).
        self._world_create_enabled = world_create_enabled
        self._worker = worker
        self._loop = loop or asyncio.get_event_loop()
        self._queue: asyncio.PriorityQueue[tuple[int, int, PaJob]] = (
            asyncio.PriorityQueue()
        )
        self._counter = itertools.count()
        self._dispatcher: asyncio.Task[None] | None = None
        self._tasks: set[asyncio.Task[None]] = set()
        self._stopped = False
        self._slot_available = concurrency
        self._slot_waiters: list[tuple[int, int, asyncio.Future[None]]] = []
        self._slot_counter = itertools.count()
        self._slot_mutex = asyncio.Lock()
        self._refresh_dedup: dict[str, asyncio.Future[PaJobResult]] = {}
        self._world_refresh_dedup: dict[str, asyncio.Future[PaJobResult]] = {}
        self._world_refresh_seen = False
        self._unit_locks: dict[str, asyncio.Lock] = {}
        self._unit_locks_mutex = asyncio.Lock()
        self._registry_lock = asyncio.Lock()

    def start(self) -> None:
        if self._disabled:
            return
        if self._dispatcher is not None:
            return
        self._stopped = False
        self._dispatcher = asyncio.create_task(self._dispatch())

    async def stop(self) -> None:
        """Cancel dispatcher + every in-flight job task immediately.

        Use `drain()` before `stop()` when you need queued jobs (e.g.
        async refresh kicked off by stale resolver) to finish first.
        `stop()` alone is appropriate only for hard tear-down where
        losing in-flight work is acceptable.
        """
        self._stopped = True
        if self._dispatcher is not None:
            self._dispatcher.cancel()
            try:
                await self._dispatcher
            except (asyncio.CancelledError, Exception):
                pass
            self._dispatcher = None
        self._cancel_queued_jobs()
        for t in list(self._tasks):
            t.cancel()
        for t in list(self._tasks):
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass
        self._tasks.clear()

    async def drain(self) -> None:
        """Wait for every queued + in-flight job to finish, then stop.

        Without this a `latest_async_refresh` policy can lose its PA
        refresh work at orchestrator shutdown: refresh jobs are queued
        without being awaited by any trial. `drain()` first waits until
        all queued jobs have been dispatched, then waits for every spawned
        job task to finish before tearing the dispatcher down.
        """
        await self._queue.join()
        if self._dispatcher is not None:
            self._dispatcher.cancel()
            try:
                await self._dispatcher
            except (asyncio.CancelledError, Exception):
                pass
            self._dispatcher = None
        # Any jobs the dispatcher spawned but did not yet complete:
        while self._tasks:
            in_flight = list(self._tasks)
            await asyncio.gather(*in_flight, return_exceptions=True)
        self._stopped = True

    @property
    def concurrency(self) -> int:
        return self._concurrency

    @property
    def disabled(self) -> bool:
        return self._disabled

    @property
    def refresh_enabled(self) -> bool:
        """True if the per-unit `refresh` PA mode is allowed to run.

        Independent of `disabled` and of `world_refresh_enabled`: when
        this is False the queue still runs failure_fix / world_refresh,
        but every `submit_refresh` resolves to a skipped future without
        marking the world stale. Resolver should gate on this before
        enqueuing per-unit refresh work; the in-queue gate is
        defense-in-depth.
        """
        return self._refresh_enabled

    @property
    def world_refresh_enabled(self) -> bool:
        """True if the world_refresh PA mode is allowed to run.

        Independent of `disabled`: when this is False the queue still
        runs failure_fix / refresh, but every `submit_world_refresh`
        resolves to a skipped future and does not mark the world as
        stale. Resolver should gate on this before materialising a
        world_refresh workdir; the in-queue gate is defense-in-depth.
        """
        return self._world_refresh_enabled

    def _skipped_future(
        self,
        *,
        job_id: str,
        kind: str,
        priority: int,
        reason: str = "PA disabled (PA_LLM_CONCURRENCY=0)",
    ) -> asyncio.Future[PaJobResult]:
        fut: asyncio.Future[PaJobResult] = self._loop.create_future()
        fut.set_result(
            PaJobResult(
                job_id=job_id,
                kind=kind,
                priority=PRIORITY_LABELS[priority],
                terminal_status="skipped",
                duration_ms=0,
                error=reason,
            )
        )
        return fut

    @property
    def world_refresh_seen(self) -> bool:
        """True once any `world_refresh` has been submitted in this run.

        Resolver / orchestrator can gate on this to skip surfacing
        per-unit `refresh` and `failure_fix` work that would race a
        stale-world fix. The queue itself also gates internally as
        defense-in-depth.
        """
        return self._world_refresh_seen

    _WORLD_REFRESH_SKIP_REASON = (
        "world_refresh started in this run; stale world makes per-unit "
        "PA pointless"
    )

    @asynccontextmanager
    async def llm_slot(self, priority: int = PRIORITY_ASYNC) -> AsyncIterator[None]:
        """Hold a `PA_LLM_CONCURRENCY` slot only around the LLM call.

        Workers MUST wrap their `pa_runner.spawn_pa_cli` call in this
        manager and MUST NOT hold the slot across deterministic ingest
        (validation, hashing, snapshotting, version write). Holding the
        slot longer would let cheap deterministic work serialise behind
        slow LLM time, contradicting the agreed split.
        """
        await self._acquire_llm_slot(priority)
        try:
            yield
        finally:
            await self._release_llm_slot()

    async def unit_write_lock(self, unit_id: str) -> asyncio.Lock:
        """Per-unit write lock for `versioning.write_new_version`."""
        async with self._unit_locks_mutex:
            lock = self._unit_locks.get(unit_id)
            if lock is None:
                lock = asyncio.Lock()
                self._unit_locks[unit_id] = lock
            return lock

    @property
    def registry_write_lock(self) -> asyncio.Lock:
        """Global lock around `instructions/registry.json` mutations.

        Only `world_refresh` mutates the registry today (appending new
        BP units). Held by `pa_decision.apply_world_refresh_decision`
        for the whole sequence of: write new unit dirs → append to
        registry → advance baseline. Per-unit `write_new_version` calls
        for `changes_refresh[]` use `unit_write_lock` as before.
        """
        return self._registry_lock

    def submit_refresh(
        self,
        *,
        unit_id: str,
        payload: dict[str, Any],
        priority: int,
    ) -> tuple[asyncio.Future[PaJobResult], bool]:
        """Enqueue or join a refresh job for `unit_id`.

        Returns (future, is_new). The dedup map is keyed by `unit_id` and
        retains the terminal future after completion, so a later resolver
        in the same run can attach and read the cached terminal result
        without re-running PA. When `is_new` is False the caller either
        joined an in-flight job or received the cached terminal result;
        the priority parameter is honoured only when `is_new` is True
        (the queue cannot reorder items mid-flight).
        """
        existing = self._refresh_dedup.get(unit_id)
        if existing is not None:
            # Either still running (caller awaits same future) or done
            # (caller gets the cached terminal result immediately).
            return existing, False
        job_id = f"pa-refresh-{int(time.time())}-{next(self._counter):04d}-{unit_id}"
        if not self._refresh_enabled:
            # Per-unit refresh gated off independently of PA. Unlike the
            # disabled-PA path below this is mode-scoped: failure_fix /
            # world_refresh must keep running, and we never touch
            # `_world_refresh_seen`. Cache the skipped future for dedup
            # parity.
            fut = self._skipped_future(
                job_id=job_id,
                kind="refresh",
                priority=priority,
                reason="refresh disabled (REFRESH_ENABLED=0)",
            )
            self._refresh_dedup[unit_id] = fut
            return fut, True
        if self._disabled:
            fut = self._skipped_future(
                job_id=job_id, kind="refresh", priority=priority
            )
            self._refresh_dedup[unit_id] = fut
            return fut, True
        if self._world_refresh_seen:
            fut = self._skipped_future(
                job_id=job_id,
                kind="refresh",
                priority=priority,
                reason=self._WORLD_REFRESH_SKIP_REASON,
            )
            self._refresh_dedup[unit_id] = fut
            return fut, True
        fut: asyncio.Future[PaJobResult] = self._loop.create_future()
        job = PaJob(
            job_id=job_id,
            kind="refresh",
            priority=priority,
            unit_ids=(unit_id,),
            payload=payload,
            future=fut,
        )
        self._refresh_dedup[unit_id] = fut
        self._queue.put_nowait((priority, next(self._counter), job))
        return fut, True

    @property
    def world_create_enabled(self) -> bool:
        """When True, world-PA jobs route through `world_create` mode."""
        return self._world_create_enabled

    def submit_world_create(
        self,
        *,
        baseline_version: str,
        payload: dict[str, Any],
        priority: int = PRIORITY_WORLD_REFRESH,
    ) -> tuple[asyncio.Future[PaJobResult], bool]:
        """Enqueue or join a `world_create` job.

        Shares the world-PA dedup map and `_world_refresh_seen` gate with
        `submit_world_refresh` so a single drift snapshot can never spawn
        both modes for the same baseline. `baseline_version` may be
        `"seed"` when the baseline is empty (one-off seed run).
        """
        existing = self._world_refresh_dedup.get(baseline_version)
        if existing is not None:
            return existing, False
        job_id = (
            f"pa-world-create-{int(time.time())}-{next(self._counter):04d}-"
            f"{baseline_version}"
        )
        self._world_refresh_seen = True
        if self._disabled:
            fut = self._skipped_future(
                job_id=job_id, kind="world_create", priority=priority
            )
            self._world_refresh_dedup[baseline_version] = fut
            return fut, True
        fut: asyncio.Future[PaJobResult] = self._loop.create_future()
        job = PaJob(
            job_id=job_id,
            kind="world_create",
            priority=priority,
            unit_ids=(),
            payload=payload,
            future=fut,
        )
        self._world_refresh_dedup[baseline_version] = fut
        self._queue.put_nowait((priority, next(self._counter), job))
        return fut, True

    def submit_world_refresh(
        self,
        *,
        baseline_version: str,
        payload: dict[str, Any],
        priority: int = PRIORITY_WORLD_REFRESH,
    ) -> tuple[asyncio.Future[PaJobResult], bool]:
        """Enqueue or join a world_refresh job for `baseline_version`.

        Returns (future, is_new). Dedup key is the baseline version: a
        single drift snapshot triggers exactly one PA job, even if
        multiple concurrent trials hit the same drift. After the job
        succeeds the new baseline lands and subsequent trials see no
        drift; the dedup entry stays cached so any late subscriber gets
        the terminal result without re-running PA.
        """
        existing = self._world_refresh_dedup.get(baseline_version)
        if existing is not None:
            return existing, False
        job_id = (
            f"pa-world-refresh-{int(time.time())}-{next(self._counter):04d}-"
            f"{baseline_version}"
        )
        if not self._world_refresh_enabled:
            # world_refresh gated off independently of PA. Unlike the
            # disabled-PA path below we deliberately do NOT flip
            # `_world_refresh_seen`: failure_fix / refresh must keep
            # running. Cache the skipped future for dedup parity.
            fut = self._skipped_future(
                job_id=job_id,
                kind="world_refresh",
                priority=priority,
                reason="world_refresh disabled (WORLD_REFRESH_ENABLED=0)",
            )
            self._world_refresh_dedup[baseline_version] = fut
            return fut, True
        # Flag flips on submit (not on completion): even a skipped /
        # rejected world_refresh means the world is known-stale in this
        # run, so per-unit PA is still pointless.
        self._world_refresh_seen = True
        if self._disabled:
            fut = self._skipped_future(
                job_id=job_id, kind="world_refresh", priority=priority
            )
            self._world_refresh_dedup[baseline_version] = fut
            return fut, True
        fut: asyncio.Future[PaJobResult] = self._loop.create_future()
        job = PaJob(
            job_id=job_id,
            kind="world_refresh",
            priority=priority,
            unit_ids=(),
            payload=payload,
            future=fut,
        )
        self._world_refresh_dedup[baseline_version] = fut
        self._queue.put_nowait((priority, next(self._counter), job))
        return fut, True

    def submit_failure_fix(
        self,
        *,
        unit_ids: tuple[str, ...],
        payload: dict[str, Any],
        mode: str = "failure_fix",
    ) -> asyncio.Future[PaJobResult]:
        """Enqueue a failure-fix job. Failure fixes are not deduped.

        `mode` is `"failure_fix"` (open eval — score available) or
        `"fix_blind"` (blind eval — no score). Workdir name and prompt
        differ; the queue stores the discriminator in `PaJob.kind`.
        """
        if mode not in ("failure_fix", "fix_blind"):
            raise ValueError(f"invalid failure-fix mode {mode!r}")
        job_id = (
            f"pa-{mode.replace('_','-')}-{int(time.time())}-{next(self._counter):04d}"
        )
        if self._disabled:
            return self._skipped_future(
                job_id=job_id,
                kind=mode,
                priority=PRIORITY_FAILURE_FIX,
            )
        if self._world_refresh_seen:
            return self._skipped_future(
                job_id=job_id,
                kind=mode,
                priority=PRIORITY_FAILURE_FIX,
                reason=self._WORLD_REFRESH_SKIP_REASON,
            )
        fut: asyncio.Future[PaJobResult] = self._loop.create_future()
        job = PaJob(
            job_id=job_id,
            kind=mode,
            priority=PRIORITY_FAILURE_FIX,
            unit_ids=unit_ids,
            payload=payload,
            future=fut,
        )
        self._queue.put_nowait((PRIORITY_FAILURE_FIX, next(self._counter), job))
        return fut

    def _cancel_queued_jobs(self) -> None:
        while True:
            try:
                _, _, job = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            if not job.future.done():
                job.future.cancel()
            self._queue.task_done()

    async def _acquire_llm_slot(self, priority: int) -> None:
        async with self._slot_mutex:
            if self._slot_available > 0 and not self._slot_waiters:
                self._slot_available -= 1
                return
            fut = self._loop.create_future()
            heapq.heappush(
                self._slot_waiters, (priority, next(self._slot_counter), fut)
            )

        try:
            await fut
        except asyncio.CancelledError:
            async with self._slot_mutex:
                if fut.done() and not fut.cancelled():
                    self._release_llm_slot_locked()
                else:
                    fut.cancel()
            raise

    async def _release_llm_slot(self) -> None:
        async with self._slot_mutex:
            self._release_llm_slot_locked()

    def _release_llm_slot_locked(self) -> None:
        while self._slot_waiters:
            _, _, fut = heapq.heappop(self._slot_waiters)
            if fut.cancelled():
                continue
            if not fut.done():
                fut.set_result(None)
                return
        self._slot_available += 1

    async def _dispatch(self) -> None:
        while not self._stopped:
            try:
                _, _, job = await self._queue.get()
            except asyncio.CancelledError:
                return
            task = asyncio.create_task(self._run_job(job))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
            self._queue.task_done()

    async def _run_job(self, job: PaJob) -> None:
        try:
            # Worker decides when to acquire `llm_slot()`. The queue
            # never holds the semaphore on the worker's behalf, so
            # deterministic ingest runs outside the LLM cap.
            result = await self._worker(self, job)
        except asyncio.CancelledError:
            if not job.future.done():
                job.future.cancel()
            return
        except Exception as exc:
            result = PaJobResult(
                job_id=job.job_id,
                kind=job.kind,
                priority=PRIORITY_LABELS[job.priority],
                terminal_status="failed",
                duration_ms=0,
                error=f"worker raised: {exc!r}",
            )
        # Refresh dedup keeps the terminal future cached so later
        # subscribers see the result without re-running PA.
        if not job.future.done():
            job.future.set_result(result)
