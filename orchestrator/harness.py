"""BitGN harness helpers (sync ConnectRPC client wrappers)."""

from __future__ import annotations

from dataclasses import dataclass

from bitgn.harness_connect import HarnessServiceClientSync
from bitgn.harness_pb2 import (
    EndTrialRequest,
    EvalPolicy,
    GetBenchmarkRequest,
    GetRunRequest,
    GetTrialRequest,
    StartRunRequest,
    StartTrialRequest,
    StatusRequest,
    SubmitRunRequest,
)


@dataclass
class TrialPlan:
    task_id: str
    trial_id: str
    harness_url: str
    instruction: str


@dataclass
class BenchmarkSummary:
    benchmark_id: str
    description: str
    is_blind: bool
    hints_by_task: dict[str, str]
    task_ids: list[str]


@dataclass(frozen=True)
class TrialVerdict:
    """Per-trial verdict surfaced by `GetRunResponse.trials[]` after submit."""

    task_id: str
    trial_id: str
    state: int  # TrialState
    score: float | None
    score_available: bool


@dataclass(frozen=True)
class RunVerdict:
    """Run-level verdict returned by `GetRun` after `SubmitRun(force=True)`."""

    run_id: str
    state: int  # RunState
    score: float | None
    score_available: bool
    trials: list[TrialVerdict]


@dataclass(frozen=True)
class TrialDetail:
    """Detailed per-trial verdict from `GetTrialResponse` — carries score_detail.

    `GetRunResponse.trials[]` (TrialHead) does not expose `score_detail`; the
    per-detail strings live only on this RPC. Used post-submit for trials we
    are about to hand to a `failure_fix` PA.
    """

    trial_id: str
    task_id: str
    state: int
    score: float | None
    score_available: bool
    score_detail: list[str]


def status(host: str) -> dict:
    client = HarnessServiceClientSync(host)
    s = client.status(StatusRequest())
    return {"status": s.status, "version": s.version}


def get_benchmark(host: str, benchmark_id: str) -> BenchmarkSummary:
    client = HarnessServiceClientSync(host)
    bench = client.get_benchmark(GetBenchmarkRequest(benchmark_id=benchmark_id))
    return BenchmarkSummary(
        benchmark_id=bench.benchmark_id,
        description=bench.description,
        is_blind=bench.policy == EvalPolicy.EVAL_POLICY_BLIND,
        hints_by_task={t.task_id: t.hint for t in bench.tasks},
        task_ids=[t.task_id for t in bench.tasks],
    )


def start_run(host: str, *, benchmark_id: str, name: str, api_key: str) -> tuple[str, list[str]]:
    client = HarnessServiceClientSync(host)
    res = client.start_run(
        StartRunRequest(benchmark_id=benchmark_id, name=name, api_key=api_key)
    )
    return res.run_id, list(res.trial_ids)


def start_trial(host: str, trial_id: str) -> TrialPlan:
    client = HarnessServiceClientSync(host)
    res = client.start_trial(StartTrialRequest(trial_id=trial_id))
    return TrialPlan(
        task_id=res.task_id,
        trial_id=res.trial_id,
        harness_url=res.harness_url,
        instruction=res.instruction,
    )


def end_trial(host: str, trial_id: str) -> None:
    """Close a trial. The harness no longer returns per-trial scores here —
    they arrive only after `submit_run` (read via `get_run`/`get_trial`).
    """
    client = HarnessServiceClientSync(host)
    client.end_trial(EndTrialRequest(trial_id=trial_id))


def submit_run(host: str, run_id: str, *, force: bool = True) -> str:
    client = HarnessServiceClientSync(host)
    res = client.submit_run(SubmitRunRequest(run_id=run_id, force=force))
    return res.run_id


def get_run(host: str, run_id: str) -> RunVerdict:
    """Fetch per-trial scores after `submit_run`."""
    client = HarnessServiceClientSync(host)
    res = client.get_run(GetRunRequest(run_id=run_id))
    trials = [
        TrialVerdict(
            task_id=t.task_id,
            trial_id=t.trial_id,
            state=t.state,
            score=t.score if t.score_available else None,
            score_available=t.score_available,
        )
        for t in res.trials
    ]
    return RunVerdict(
        run_id=res.run_id,
        state=res.state,
        score=res.score if res.score_available else None,
        score_available=res.score_available,
        trials=trials,
    )


def get_trial(host: str, trial_id: str) -> TrialDetail:
    """Fetch one trial's score_detail strings (post-submit, per-trial RPC)."""
    client = HarnessServiceClientSync(host)
    res = client.get_trial(GetTrialRequest(trial_id=trial_id, cursor=0))
    return TrialDetail(
        trial_id=res.trial_id,
        task_id=res.task_id,
        state=res.state,
        score=res.score if res.score_available else None,
        score_available=res.score_available,
        score_detail=list(res.score_detail),
    )
