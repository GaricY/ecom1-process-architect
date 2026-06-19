"""Environment-driven configuration for the ECOM agent orchestrator."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

EffortLevel = Literal["low", "medium", "high", "xhigh", "max"]
VALID_EFFORTS: tuple[EffortLevel, ...] = ("low", "medium", "high", "xhigh", "max")


@dataclass
class Config:
    bitgn_api_key: str
    benchmark_host: str
    benchmark_id: str
    run_name: str

    claude_bin: str
    claude_model: str
    claude_reasoning_effort: EffortLevel
    claude_max_turns: int

    pa_claude_model: str
    pa_claude_reasoning_effort: EffortLevel
    pa_max_turns: int

    concurrency: int
    pa_llm_concurrency: int
    world_refresh_enabled: bool
    world_create_enabled: bool
    pa_apply: bool
    pa_fix_enabled: bool
    refresh_enabled: bool
    trial_start_interval_sec: int
    stale_resolution: str
    process_architect_timeout_sec: int
    process_architect_world_timeout_sec: int
    pa_conflict_mode: bool
    pa_conflict_max_retries: int
    blind_emulation: bool
    dump_sql_rows: int

    runs_root: str
    smoke_task: str


def _coerce_effort(value: str | None, default: EffortLevel = "medium") -> EffortLevel:
    if not value:
        return default
    lowered = value.lower()
    if lowered not in VALID_EFFORTS:
        raise ValueError(
            f"invalid CLAUDE_REASONING_EFFORT={value!r}; choose one of {VALID_EFFORTS}"
        )
    return lowered  # type: ignore[return-value]


def _coerce_int(value: str | None, default: int, *, name: str) -> int:
    if not value:
        return default
    try:
        n = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}") from exc
    if n < 1:
        raise ValueError(f"{name} must be >= 1, got {n}")
    return n


def _coerce_nonneg_int(value: str | None, default: int, *, name: str) -> int:
    if not value:
        return default
    try:
        n = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}") from exc
    if n < 0:
        raise ValueError(f"{name} must be >= 0, got {n}")
    return n


VALID_STALE_RESOLUTIONS: tuple[str, ...] = (
    "latest_async_refresh",
    "wait_for_refresh",
)


def _coerce_stale_resolution(value: str | None, default: str = "latest_async_refresh") -> str:
    if not value:
        return default
    if value not in VALID_STALE_RESOLUTIONS:
        raise ValueError(
            f"invalid STALE_RESOLUTION={value!r}; choose one of {VALID_STALE_RESOLUTIONS}"
        )
    return value


_BOOL_TRUE = {"1", "true", "yes", "on", "enabled", "enable"}
_BOOL_FALSE = {"0", "false", "no", "off", "disabled", "disable"}


def _coerce_bool(value: str | None, default: bool, *, name: str) -> bool:
    if value is None or value == "":
        return default
    lowered = value.strip().lower()
    if lowered in _BOOL_TRUE:
        return True
    if lowered in _BOOL_FALSE:
        return False
    raise ValueError(f"{name} must be a boolean, got {value!r}")


def load_config(env: dict[str, str | None] | None = None) -> Config:
    e = env if env is not None else os.environ
    concurrency = _coerce_int(e.get("CONCURRENCY"), 1, name="CONCURRENCY")
    return Config(
        bitgn_api_key=e.get("BITGN_API_KEY") or "",
        benchmark_host=(
            e.get("BITGN_HOST") or e.get("BENCHMARK_HOST") or "https://api.bitgn.com"
        ),
        benchmark_id=(
            e.get("BENCHMARK_ID") or e.get("BENCH_ID") or "bitgn/ecom1-dev"
        ),
        run_name=e.get("RUN_NAME") or "@GaricY Process Architect postmortem",
        claude_bin=e.get("CLAUDE_BIN") or "claude",
        claude_model=e.get("CLAUDE_MODEL") or "claude-sonnet-4-6",
        claude_reasoning_effort=_coerce_effort(
            e.get("CLAUDE_REASONING_EFFORT"), default="medium"
        ),
        claude_max_turns=_coerce_int(
            e.get("CLAUDE_MAX_TURNS"), 40, name="CLAUDE_MAX_TURNS"
        ),
        pa_claude_model=e.get("PA_CLAUDE_MODEL") or "claude-opus-4-8",
        pa_claude_reasoning_effort=_coerce_effort(
            e.get("PA_CLAUDE_REASONING_EFFORT"), default="xhigh"
        ),
        pa_max_turns=_coerce_nonneg_int(
            e.get("PA_MAX_TURNS"), 0, name="PA_MAX_TURNS"
        ),
        concurrency=concurrency,
        pa_llm_concurrency=_coerce_nonneg_int(
            e.get("PA_LLM_CONCURRENCY"), 1, name="PA_LLM_CONCURRENCY"
        ),
        world_refresh_enabled=_coerce_bool(
            e.get("WORLD_REFRESH_ENABLED"), False, name="WORLD_REFRESH_ENABLED"
        ),
        world_create_enabled=_coerce_bool(
            e.get("WORLD_CREATE_ENABLED"), False, name="WORLD_CREATE_ENABLED"
        ),
        pa_apply=_coerce_bool(
            e.get("PA_APPLY"), True, name="PA_APPLY"
        ),
        pa_fix_enabled=_coerce_bool(
            e.get("PA_FIX_ENABLED"), False, name="PA_FIX_ENABLED"
        ),
        refresh_enabled=_coerce_bool(
            e.get("REFRESH_ENABLED"), False, name="REFRESH_ENABLED"
        ),
        trial_start_interval_sec=_coerce_nonneg_int(
            e.get("TRIAL_START_INTERVAL_SEC"),
            2,
            name="TRIAL_START_INTERVAL_SEC",
        ),
        stale_resolution=_coerce_stale_resolution(
            e.get("STALE_RESOLUTION"), default="latest_async_refresh"
        ),
        process_architect_timeout_sec=_coerce_int(
            e.get("PROCESS_ARCHITECT_TIMEOUT_SEC"), 1200,
            name="PROCESS_ARCHITECT_TIMEOUT_SEC",
        ),
        process_architect_world_timeout_sec=_coerce_int(
            e.get("PROCESS_ARCHITECT_WORLD_TIMEOUT_SEC"), 7200,
            name="PROCESS_ARCHITECT_WORLD_TIMEOUT_SEC",
        ),
        pa_conflict_mode=_coerce_bool(
            e.get("PA_CONFLICT_MODE"), True, name="PA_CONFLICT_MODE"
        ),
        pa_conflict_max_retries=_coerce_nonneg_int(
            e.get("PA_CONFLICT_MAX_RETRIES"), 1,
            name="PA_CONFLICT_MAX_RETRIES",
        ),
        blind_emulation=_coerce_bool(
            e.get("BLIND_EMULATION"), False, name="BLIND_EMULATION"
        ),
        dump_sql_rows=_coerce_nonneg_int(
            e.get("DUMP_SQL_ROWS"), 0, name="DUMP_SQL_ROWS"
        ),
        runs_root=e.get("RUNS_ROOT") or "../.runs/ecom",
        smoke_task=e.get("SMOKE_TASK") or "t01",
    )
