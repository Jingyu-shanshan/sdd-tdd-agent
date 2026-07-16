import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Optional

from sdd_tdd_agent.analyze_command import ActiveSessionError, load_analyzer_config
from sdd_tdd_agent.model_adapter import (
    CodexCommandResolver,
    CommandAnalyzerConfig,
    ProcessRunner,
)
from sdd_tdd_agent.project_status import load_project_status
from sdd_tdd_agent.red_execution import record_test_source_artifact
from sdd_tdd_agent.tdd_cycle import prepare_write_test_cycle
from sdd_tdd_agent.test_source_adapter import (
    CodexExecTestSourceGenerator,
    JsonCommandTestSourceGenerator,
)
from sdd_tdd_agent.test_source_generation import (
    GeneratedTestSource,
    TestSourceGenerationRequest,
    load_test_source_generation_request,
)
from sdd_tdd_agent.test_source_workspace import (
    AtomicTestSourceWriter,
    TestSourceCollector,
    TestSourceWriter,
    WorkspaceSourceCollector,
)


@dataclass(frozen=True)
class TestSourceCommandRun:
    """Result of generating and writing one active planned test source."""

    __test__: ClassVar[bool] = False

    session_id: str
    cycle_number: int
    test_id: str
    file_path: str


def _generate_source(
    config: CommandAnalyzerConfig,
    runner: ProcessRunner,
    request: TestSourceGenerationRequest,
    command_resolver: Optional[CodexCommandResolver],
) -> GeneratedTestSource:
    if config.protocol != "codex-exec":
        return JsonCommandTestSourceGenerator(config, runner).generate(request)
    with tempfile.TemporaryDirectory(prefix="sdd-tdd-test-context-") as path:
        generator = CodexExecTestSourceGenerator(
            config,
            runner,
            Path(path),
            command_resolver=command_resolver,
        )
        return generator.generate(request)


def generate_active_test_source(
    root: Path,
    runner: ProcessRunner,
    source_collector: Optional[TestSourceCollector] = None,
    command_resolver: Optional[CodexCommandResolver] = None,
    writer: Optional[TestSourceWriter] = None,
) -> TestSourceCommandRun:
    """Generate and atomically write one test for the active project Session."""
    status = load_project_status(root)
    if status.current_session is None:
        raise ActiveSessionError("Project has no active Session")
    config = load_analyzer_config(root)
    prepared = prepare_write_test_cycle(root, status.current_session)
    collector = source_collector or WorkspaceSourceCollector()
    sources = collector.collect(root, prepared.test_case.test_file)
    request = load_test_source_generation_request(
        root,
        status.current_session,
        sources,
    )
    generated = _generate_source(config, runner, request, command_resolver)
    target_writer = writer or AtomicTestSourceWriter()
    target_writer.write(root, request, generated)
    record_test_source_artifact(root, status.current_session, generated)
    return TestSourceCommandRun(
        session_id=status.current_session,
        cycle_number=prepared.cycle_number,
        test_id=generated.test_id,
        file_path=generated.file_path,
    )
