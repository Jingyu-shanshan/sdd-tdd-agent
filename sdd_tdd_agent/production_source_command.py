import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Dict, Optional

from sdd_tdd_agent.analyze_command import ActiveSessionError
from sdd_tdd_agent.model_adapter import (
    CodexCommandResolver,
    CommandAnalyzerConfig,
    ProcessRunner,
    structured_cli_runner,
)
from sdd_tdd_agent.production_source_adapter import (
    CodexExecProductionSourceGenerator,
    JsonCommandProductionSourceGenerator,
)
from sdd_tdd_agent.production_source_generation import (
    GeneratedProductionSource,
    ProductionSourceGenerator,
    ProductionSourceGenerationRequest,
    load_production_source_generation_request,
    load_production_source_roots,
    production_source_path,
    validate_generated_production_source,
)
from sdd_tdd_agent.production_source_workspace import (
    AtomicProductionSourceWriter,
    ProductionSourceCollector,
    ProductionSourceWriter,
    WorkspaceProductionSourceCollector,
)
from sdd_tdd_agent.project_status import load_project_status
from sdd_tdd_agent.provider_registry import load_provider_config
from sdd_tdd_agent.red_execution import (
    RedExecutionError,
    validate_current_test_source_artifact,
)
from sdd_tdd_agent.tdd_cycle import load_current_test_case


@dataclass(frozen=True)
class ProductionSourceCommandRun:
    """Result of writing one Blind production source for the current test."""

    __test__: ClassVar[bool] = False

    session_id: str
    cycle_number: int
    test_id: str
    file_path: str


def _generator(
    root: Path,
    config: CommandAnalyzerConfig,
    runner: ProcessRunner,
    command_resolver: Optional[CodexCommandResolver],
) -> ProductionSourceGenerator:
    if config.protocol == "codex-exec":
        return CodexExecProductionSourceGenerator(
            config,
            runner,
            root,
            command_resolver=command_resolver,
        )
    return JsonCommandProductionSourceGenerator(
        config,
        structured_cli_runner(config, runner),
    )


def _state(root: Path, session_id: str) -> tuple[Path, str, Dict[str, object]]:
    state_path = root / ".agent" / "sessions" / session_id / "state.json"
    try:
        raw = _read_state_text(state_path)
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RedExecutionError("Session state could not be read") from error
    if not isinstance(value, dict):
        raise RedExecutionError("Session state must be a JSON object")
    return state_path, raw, value


def _read_state_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise RedExecutionError("Session state could not be read") from error


def _write_state(path: Path, state: Dict[str, object]) -> None:
    temporary = path.with_name(".state.json.production-source.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            stream.write(f"{json.dumps(state, indent=2)}\n")
        temporary.replace(path)
    except FileExistsError as error:
        raise RedExecutionError(
            "Session state update is already in progress"
        ) from error
    except OSError as error:
        if temporary.exists():
            temporary.unlink()
        raise RedExecutionError("Session state could not be updated") from error


def _ensure_state_update_available(state_path: Path) -> None:
    temporary = state_path.with_name(".state.json.production-source.tmp")
    if temporary.exists():
        raise RedExecutionError("Session state update is already in progress")


def _record_production_source(
    root: Path,
    session_id: str,
    request: ProductionSourceGenerationRequest,
    generated: GeneratedProductionSource,
    expected_state: str,
) -> None:
    state_path, raw_state, state = _state(root, session_id)
    if raw_state != expected_state:
        raise RedExecutionError("Session state changed concurrently")
    case = load_current_test_case(root, session_id, "RED")
    validate_current_test_source_artifact(root, session_id, "RED")
    validate_generated_production_source(request, generated)
    if case.test_id != generated.test_id:
        raise RedExecutionError("Production source does not match current test")
    relative = production_source_path(
        generated.file_path,
        request.production_source_roots,
    )
    target = root.resolve().joinpath(*relative.parts)
    try:
        content = target.read_bytes()
    except OSError as error:
        raise RedExecutionError("Production source could not be verified") from error
    if content != generated.content.encode("utf-8"):
        raise RedExecutionError("Production source changed after writing")
    if _read_state_text(state_path) != raw_state:
        raise RedExecutionError("Session state changed concurrently")
    progress = state.get("tdd_cycle")
    if not isinstance(progress, dict) or progress.get("phase") != "RED":
        raise RedExecutionError("Current TDD cycle must be in RED phase")
    progress["phase"] = "IMPLEMENT"
    production_record = {
        "test_id": generated.test_id,
        "file_path": generated.file_path,
        "sha256": hashlib.sha256(content).hexdigest(),
    }
    if request.production_source_roots != ("src",):
        production_record["source_root"] = request.production_source_roots[0]
    state["production_source"] = production_record
    state.pop("green_evidence", None)
    if _read_state_text(state_path) != raw_state:
        raise RedExecutionError("Session state changed concurrently")
    _write_state(state_path, state)


def generate_active_production_source(
    root: Path,
    runner: ProcessRunner,
    collector: Optional[ProductionSourceCollector] = None,
    command_resolver: Optional[CodexCommandResolver] = None,
    writer: Optional[ProductionSourceWriter] = None,
) -> ProductionSourceCommandRun:
    """Generate, safely write, and record one active Blind source change."""
    status = load_project_status(root)
    if status.current_session is None:
        raise ActiveSessionError("Project has no active Session")
    session_id = status.current_session
    config = load_provider_config(root, "production-source")
    state_path, initial_raw, initial_state = _state(root, session_id)
    _ensure_state_update_available(state_path)
    cycle = initial_state.get("current_cycle")
    if isinstance(cycle, bool) or not isinstance(cycle, int) or cycle <= 0:
        raise RedExecutionError("Session cycle number is invalid")
    source_roots = load_production_source_roots(root, session_id, "RED")
    source_collector = collector or WorkspaceProductionSourceCollector()
    sources = source_collector.collect(root, source_roots)
    request = load_production_source_generation_request(
        root,
        session_id,
        sources,
        source_roots,
    )
    generated = _generator(root, config, runner, command_resolver).generate(request)
    validate_current_test_source_artifact(root, session_id, "RED")
    if _state(root, session_id)[1] != initial_raw:
        raise RedExecutionError("Session state changed concurrently")
    target_writer = writer or AtomicProductionSourceWriter()
    target_writer.write(root, request, generated)
    _record_production_source(
        root,
        session_id,
        request,
        generated,
        initial_raw,
    )
    return ProductionSourceCommandRun(
        session_id,
        cycle,
        generated.test_id,
        generated.file_path,
    )
