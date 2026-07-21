import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

from sdd_tdd_agent.telemetry import (
    TelemetryEvent,
    load_session_events,
    load_session_metrics,
)
from sdd_tdd_agent.tdd_cycle import load_planned_test_cases


class QualityMetricsError(RuntimeError):
    """Safe public error for state/plan-derived quality metrics."""


@dataclass(frozen=True)
class SessionQualityMetrics:
    """Exact task, test, and execution quality projection for one Session."""

    session_id: str
    planned_tasks: int
    completed_tasks: int
    task_completion_rate: float
    planned_tests: int
    completed_tests: int
    test_completion_rate: float
    build_test_success_rate: Optional[float]
    refactor_success_rate: Optional[float]
    mean_call_duration_seconds: Optional[float]
    cost_per_feature_usd: Optional[float]


def _state(root: Path, session_id: str) -> Dict[str, object]:
    path = root / ".agent" / "sessions" / session_id / "state.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise QualityMetricsError("Quality metric state is invalid") from error
    if not isinstance(value, dict) or value.get("session_id") != session_id:
        raise QualityMetricsError("Quality metric state is invalid")
    return value


def _completed_tests(state: Dict[str, object]) -> Tuple[str, ...]:
    completion = state.get("implementation_completion")
    progress = state.get("tdd_cycle")
    value: object = None
    if isinstance(completion, dict):
        value = completion.get("completed_tests")
    elif isinstance(progress, dict):
        value = progress.get("completed_tests")
    if value is None:
        return ()
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise QualityMetricsError("Completed test metrics are invalid")
    return tuple(value)


def _rate(events: Tuple[TelemetryEvent, ...]) -> Optional[float]:
    if not events:
        return None
    return sum(event.success for event in events) / len(events)


def load_session_quality_metrics(
    root: Path,
    session_id: str,
) -> SessionQualityMetrics:
    """Derive exact quality rates from validated plans, state, and telemetry."""
    try:
        cases = load_planned_test_cases(root, session_id)
        events = load_session_events(root, session_id)
        aggregate = load_session_metrics(root, session_id)
    except (OSError, UnicodeError, ValueError) as error:
        raise QualityMetricsError("Quality metric inputs are invalid") from error
    state = _state(root, session_id)
    completed = _completed_tests(state)
    case_ids = tuple(case.test_id for case in cases)
    if completed != case_ids[: len(completed)]:
        raise QualityMetricsError("Completed test metrics are stale")
    task_ids = tuple(dict.fromkeys(case.task_id for case in cases))
    completed_set: Set[str] = set(completed)
    completed_tasks = sum(
        all(case.test_id in completed_set for case in cases if case.task_id == task_id)
        for task_id in task_ids
    )
    test_events = tuple(event for event in events if event.kind == "test")
    refactor_events = tuple(
        event
        for event in test_events
        if event.operation
        in {"refactor_verification", "automated_refactor_verification"}
    )
    mean_duration = (
        round(sum(event.duration_seconds for event in events) / len(events), 6)
        if events
        else None
    )
    cost = aggregate.cost_usd if state.get("kind") == "feature" else None
    return SessionQualityMetrics(
        session_id,
        len(task_ids),
        completed_tasks,
        completed_tasks / len(task_ids),
        len(cases),
        len(completed),
        len(completed) / len(cases),
        _rate(test_events),
        _rate(refactor_events),
        mean_duration,
        cost,
    )


def _percent(value: Optional[float]) -> str:
    return f"{value:.2%}" if value is not None else "unavailable"


def render_session_quality_metrics(metrics: SessionQualityMetrics) -> str:
    """Render deterministic task/test and execution quality metrics."""
    duration = (
        f"{metrics.mean_call_duration_seconds:.6f}s"
        if metrics.mean_call_duration_seconds is not None
        else "unavailable"
    )
    cost = (
        f"{metrics.cost_per_feature_usd:.6f}"
        if metrics.cost_per_feature_usd is not None
        else "unavailable"
    )
    return (
        f"Session quality: {metrics.session_id}\n"
        f"Tasks: {metrics.completed_tasks}/{metrics.planned_tasks} "
        f"({_percent(metrics.task_completion_rate)})\n"
        f"Tests: {metrics.completed_tests}/{metrics.planned_tests} "
        f"({_percent(metrics.test_completion_rate)})\n"
        f"Build/test success: {_percent(metrics.build_test_success_rate)}\n"
        f"Refactor success: {_percent(metrics.refactor_success_rate)}\n"
        f"Mean call duration: {duration}\n"
        f"Cost per feature USD: {cost}\n"
    )
