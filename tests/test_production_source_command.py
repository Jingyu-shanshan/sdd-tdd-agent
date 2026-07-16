import hashlib
import io
import json
from pathlib import Path
from typing import Optional, Tuple

import pytest

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.green_verification import GreenVerificationRun
from sdd_tdd_agent.implementation_command import continue_active_implementation
from sdd_tdd_agent.model_adapter import ProcessResult
from sdd_tdd_agent.production_source_adapter import ProductionSourceGeneratorError
from sdd_tdd_agent.production_source_command import ProductionSourceCommandRun
from sdd_tdd_agent.production_source_command import generate_active_production_source
from sdd_tdd_agent.production_source_generation import GeneratedProductionSource
from sdd_tdd_agent.production_source_generation import ProductionSourceGenerationRequest
from sdd_tdd_agent.production_source_workspace import (
    ProductionSourceWriter,
    ProductionSourceWriteResult,
)
from sdd_tdd_agent.red_execution import RedExecutionError, TestCommandProcessResult
from tests.production_source_support import (
    GENERATED_CONTENT,
    PRODUCTION_CONTENT,
    create_red_workspace,
)


class ProductionRunner:
    def __init__(
        self,
        returncode: int = 0,
        file_path: str = "src/export.ts",
    ) -> None:
        self.returncode = returncode
        self.file_path = file_path
        self.calls = 0
        self.stdin: Optional[str] = None

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.calls += 1
        self.stdin = stdin
        response = {
            "test_id": "TC1",
            "file_path": self.file_path,
            "content": GENERATED_CONTENT,
        }
        return ProcessResult(self.returncode, json.dumps(response), "SECRET")


class UnexpectedTestRunner:
    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> TestCommandProcessResult:
        raise AssertionError("Test runner must not be called during implementation")


class PassingTestRunner:
    def __init__(self) -> None:
        self.calls = 0

    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> TestCommandProcessResult:
        self.calls += 1
        return TestCommandProcessResult(0, "passed\n", "")


class NoWriteWriter:
    def write(
        self,
        root: Path,
        request: ProductionSourceGenerationRequest,
        generated: GeneratedProductionSource,
    ) -> ProductionSourceWriteResult:
        return ProductionSourceWriteResult(generated.file_path, True)


class WrongContentWriter:
    def write(
        self,
        root: Path,
        request: ProductionSourceGenerationRequest,
        generated: GeneratedProductionSource,
    ) -> ProductionSourceWriteResult:
        (root / "src" / "export.ts").write_text("wrong\n")
        return ProductionSourceWriteResult(generated.file_path, True)


class StateChangingRunner(ProductionRunner):
    def __init__(self, session: Path) -> None:
        super().__init__()
        self.session = session

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        result = super().run(command, stdin, timeout_seconds)
        state_path = self.session / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["concurrent"] = True
        state_path.write_text(json.dumps(state), encoding="utf-8")
        return result


class StateChangingWriter:
    def __init__(self, session: Path) -> None:
        self.session = session

    def write(
        self,
        root: Path,
        request: ProductionSourceGenerationRequest,
        generated: GeneratedProductionSource,
    ) -> ProductionSourceWriteResult:
        (root / "src" / "export.ts").write_text(generated.content)
        state_path = self.session / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["concurrent"] = True
        state_path.write_text(json.dumps(state), encoding="utf-8")
        return ProductionSourceWriteResult(generated.file_path, True)


class CommandCodexRunner:
    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        output = Path(command[command.index("--output-last-message") + 1])
        output.write_text(
            json.dumps(
                {
                    "test_id": "TC1",
                    "file_path": "src/export.ts",
                    "content": GENERATED_CONTENT,
                }
            ),
            encoding="utf-8",
        )
        return ProcessResult(0, "", "")


def test_should_generate_write_and_record_one_blind_production_source(
    tmp_path: Path,
) -> None:
    session = create_red_workspace(tmp_path)
    runner = ProductionRunner()

    run = continue_active_implementation(
        tmp_path,
        runner,
        UnexpectedTestRunner(),
    )

    assert isinstance(run, ProductionSourceCommandRun)
    assert run.session_id == "feature-1"
    assert run.test_id == "TC1"
    assert run.file_path == "src/export.ts"
    assert runner.calls == 1
    assert runner.stdin is not None
    for forbidden in (
        "REQUIREMENT-SENTINEL",
        "DESIGN-SENTINEL",
        "TASK-SENTINEL",
    ):
        assert forbidden not in runner.stdin
    assert (tmp_path / "src" / "export.ts").read_text() == GENERATED_CONTENT
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["tdd_cycle"]["phase"] == "IMPLEMENT"
    assert state["production_source"] == {
        "test_id": "TC1",
        "file_path": "src/export.ts",
        "sha256": hashlib.sha256(GENERATED_CONTENT.encode()).hexdigest(),
    }


def test_should_render_production_source_cli_output(tmp_path: Path) -> None:
    create_red_workspace(tmp_path)
    output = io.StringIO()

    exit_code = main(
        ["continue"],
        out=output,
        root=tmp_path,
        runner=ProductionRunner(),
        test_runner=UnexpectedTestRunner(),
    )

    assert exit_code == 0
    assert output.getvalue() == (
        "Production source ready for GREEN: feature-1 (TC1 -> src/export.ts)\n"
    )


def test_should_preserve_red_and_source_when_provider_fails(tmp_path: Path) -> None:
    session = create_red_workspace(tmp_path)
    before_state = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(ProductionSourceGeneratorError, match="exit code 7"):
        continue_active_implementation(
            tmp_path,
            ProductionRunner(returncode=7),
            UnexpectedTestRunner(),
        )

    assert (session / "state.json").read_text(encoding="utf-8") == before_state
    assert (tmp_path / "src" / "export.ts").read_text() == PRODUCTION_CONTENT


def test_should_verify_green_during_implement_without_second_model_call(
    tmp_path: Path,
) -> None:
    create_red_workspace(tmp_path)
    runner = ProductionRunner()
    continue_active_implementation(tmp_path, runner, UnexpectedTestRunner())
    test_runner = PassingTestRunner()

    run = continue_active_implementation(tmp_path, runner, test_runner)

    assert isinstance(run, GreenVerificationRun)
    assert runner.calls == 1
    assert test_runner.calls == 2


def test_should_reject_missing_active_session(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "project.yml").write_text("name: reports\n")

    with pytest.raises(ValueError, match="no active Session"):
        generate_active_production_source(tmp_path, ProductionRunner())


def test_should_reject_invalid_cycle_before_model_or_source_write(
    tmp_path: Path,
) -> None:
    session = create_red_workspace(tmp_path)
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    state["current_cycle"] = False
    (session / "state.json").write_text(json.dumps(state), encoding="utf-8")
    runner = ProductionRunner()

    with pytest.raises(RedExecutionError, match="cycle number"):
        generate_active_production_source(tmp_path, runner)

    assert runner.calls == 0
    assert (tmp_path / "src" / "export.ts").read_text() == PRODUCTION_CONTENT


def test_should_reject_preexisting_state_update_before_model_or_write(
    tmp_path: Path,
) -> None:
    session = create_red_workspace(tmp_path)
    (session / ".state.json.production-source.tmp").write_text("occupied")
    runner = ProductionRunner()

    with pytest.raises(RedExecutionError, match="already in progress"):
        generate_active_production_source(tmp_path, runner)

    assert runner.calls == 0
    assert (tmp_path / "src" / "export.ts").read_text() == PRODUCTION_CONTENT


def test_should_reject_state_changed_during_model_before_source_write(
    tmp_path: Path,
) -> None:
    session = create_red_workspace(tmp_path)

    with pytest.raises(RedExecutionError, match="changed concurrently"):
        generate_active_production_source(
            tmp_path,
            StateChangingRunner(session),
        )

    assert (tmp_path / "src" / "export.ts").read_text() == PRODUCTION_CONTENT


def test_should_reject_state_changed_during_source_write(tmp_path: Path) -> None:
    session = create_red_workspace(tmp_path)

    with pytest.raises(RedExecutionError, match="changed concurrently"):
        generate_active_production_source(
            tmp_path,
            ProductionRunner(),
            writer=StateChangingWriter(session),
        )

    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["tdd_cycle"]["phase"] == "RED"
    assert "production_source" not in state


def test_should_reject_writer_that_did_not_create_new_source(tmp_path: Path) -> None:
    session = create_red_workspace(tmp_path)
    before = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(RedExecutionError, match="could not be verified"):
        generate_active_production_source(
            tmp_path,
            ProductionRunner(file_path="src/new.ts"),
            writer=NoWriteWriter(),
        )

    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_compose_codex_blind_production_generator(tmp_path: Path) -> None:
    session = create_red_workspace(tmp_path)
    config = tmp_path / ".agent" / "config.yml"
    config.write_text(
        """\
requirement_analyzer_protocol: codex-exec
requirement_analyzer_command:
  - "codex"
requirement_analyzer_timeout_seconds: 30
test_command_timeout_seconds: 15
""",
        encoding="utf-8",
    )

    run = generate_active_production_source(tmp_path, CommandCodexRunner())

    assert run.file_path == "src/export.ts"
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["tdd_cycle"]["phase"] == "IMPLEMENT"


@pytest.mark.parametrize("writer", [NoWriteWriter(), WrongContentWriter()])
def test_should_reject_writer_that_did_not_write_exact_generated_source(
    tmp_path: Path,
    writer: ProductionSourceWriter,
) -> None:
    session = create_red_workspace(tmp_path)
    before = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(RedExecutionError, match="changed after writing"):
        generate_active_production_source(
            tmp_path,
            ProductionRunner(),
            writer=writer,
        )

    assert (session / "state.json").read_text(encoding="utf-8") == before
