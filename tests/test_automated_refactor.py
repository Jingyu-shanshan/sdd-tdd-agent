import hashlib
import io
import json
from pathlib import Path
from typing import Optional, Tuple, cast

import pytest

from sdd_tdd_agent.automated_refactor import (
    AUTOMATED_REFACTOR_SCHEMA,
    AutomatedRefactorError,
    AutomatedRefactorRequest,
    CodexExecAutomatedRefactorGenerator,
    GeneratedAutomatedRefactor,
    JsonCommandAutomatedRefactorGenerator,
    apply_active_automated_refactor,
    load_automated_refactor_request,
    validate_generated_automated_refactor,
)
from sdd_tdd_agent.cli import main
from sdd_tdd_agent.implementation_review import run_active_implementation_review
from sdd_tdd_agent.model_adapter import (
    CommandAnalyzerConfig,
    ProcessResult,
)
from sdd_tdd_agent.red_execution import TestCommandProcessResult
from sdd_tdd_agent.semantic_review import (
    GeneratedSemanticReview,
    SemanticFinding,
    SemanticReviewRequest,
    run_semantic_review,
)
from tests.implementation_review_support import create_review_workspace
from tests.refactor_completion_support import create_refactor_workspace


REFACTORED_CONTENT = """\
const REPORT = 'report'

export function exportReport(): string {
  return REPORT
}
"""
PASS = TestCommandProcessResult(0, "passed\n", "")
SUITE_PASS = TestCommandProcessResult(0, "all tests passed\n", "")


class ApprovedReviewer:
    def review(self, request: SemanticReviewRequest) -> GeneratedSemanticReview:
        return GeneratedSemanticReview(
            "The implementation is safe to simplify.",
            (
                SemanticFinding(
                    "R1",
                    "readability",
                    "warning",
                    "src/export.ts",
                    1,
                    "The report value is embedded in the function.",
                    "Name the report value without changing the public API.",
                ),
            ),
            "approved",
        )


class StaticGenerator:
    def __init__(self, generated: GeneratedAutomatedRefactor) -> None:
        self.generated = generated
        self.requests: list[AutomatedRefactorRequest] = []

    def generate(
        self,
        request: AutomatedRefactorRequest,
    ) -> GeneratedAutomatedRefactor:
        self.requests.append(request)
        return self.generated


class SequenceTestRunner:
    def __init__(self, results: Tuple[TestCommandProcessResult, ...]) -> None:
        self.results = results
        self.calls: list[Tuple[str, ...]] = []

    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> TestCommandProcessResult:
        self.calls.append(command)
        return self.results[len(self.calls) - 1]


class JsonProcessRunner:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.calls: list[tuple[Tuple[str, ...], str, float]] = []

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.calls.append((command, stdin, timeout_seconds))
        return ProcessResult(0, json.dumps(self.response), "")


class CodexProcessRunner:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.workspace: Optional[Path] = None

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.workspace = Path(command[command.index("--cd") + 1])
        output = Path(command[command.index("--output-last-message") + 1])
        output.write_text(json.dumps(self.response), encoding="utf-8")
        return ProcessResult(0, "", "")


class FixedResolver:
    def resolve(self, executable: str) -> str:
        return "resolved-codex"


class FailingProcessRunner:
    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        return ProcessResult(7, stdin, stdin)


class MissingCodexOutputRunner:
    def __init__(self, returncode: int) -> None:
        self.returncode = returncode

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        return ProcessResult(self.returncode, "", "")


class RawProcessRunner:
    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        return ProcessResult(0, "not-json", "")


class MutatingGenerator(StaticGenerator):
    def __init__(
        self,
        generated: GeneratedAutomatedRefactor,
        state_path: Path,
    ) -> None:
        super().__init__(generated)
        self.state_path = state_path

    def generate(
        self,
        request: AutomatedRefactorRequest,
    ) -> GeneratedAutomatedRefactor:
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        state["concurrent_change"] = True
        self.state_path.write_text(json.dumps(state), encoding="utf-8")
        return super().generate(request)


def _workspace(root: Path) -> Path:
    session = create_review_workspace(root)
    run_semantic_review(root, "feature-1", ApprovedReviewer())
    run_active_implementation_review(root)
    return session


def _generated(
    file_path: str = "src/export.ts",
    content: str = REFACTORED_CONTENT,
) -> GeneratedAutomatedRefactor:
    return GeneratedAutomatedRefactor(
        file_path,
        content,
        "Named the stable report value without changing behavior.",
    )


def test_should_load_only_digest_bound_refactor_context(tmp_path: Path) -> None:
    session = _workspace(tmp_path)

    request = load_automated_refactor_request(tmp_path, "feature-1")

    assert request.prompt_version == "v1"
    assert "behavior-preserving" in request.prompt
    assert request.source.path == "src/export.ts"
    assert "return 'report'" in request.source.content
    assert request.completion_sha256 in (session / "state.json").read_text()
    assert request.review_sha256 in (session / "state.json").read_text()
    serialized = json.dumps(request.__dict__, default=lambda value: value.__dict__)
    assert "REQUIREMENT-SENTINEL" not in serialized
    assert "DESIGN-SENTINEL" not in serialized
    assert "TASK-SENTINEL" not in serialized
    assert "exports report failed" not in serialized


def test_should_apply_refactor_verify_tests_and_enter_done(tmp_path: Path) -> None:
    session = _workspace(tmp_path)
    source = tmp_path / "src" / "export.ts"
    before_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    runner = SequenceTestRunner((PASS, SUITE_PASS))

    run = apply_active_automated_refactor(
        tmp_path,
        StaticGenerator(_generated()),
        runner,
    )

    assert run.session_id == "feature-1"
    assert run.file_path == "src/export.ts"
    assert run.before_sha256 == before_sha
    assert run.after_sha256 == hashlib.sha256(REFACTORED_CONTENT.encode()).hexdigest()
    assert source.read_text() == REFACTORED_CONTENT
    assert len(runner.calls) == 2
    state = json.loads((session / "state.json").read_text())
    assert state["state"] == "DONE"
    assert state["refactor"] == {
        "mode": "automated_source_change",
        "decision": "verified",
        "file_path": "src/export.ts",
        "before_sha256": run.before_sha256,
        "after_sha256": run.after_sha256,
    }


@pytest.mark.parametrize(
    ("generated", "message"),
    [
        (_generated("src/other.ts"), "exact final production"),
        (
            _generated(
                content="export function exportReport(): string {\n  return 'report'\n}\n"
            ),
            "must change",
        ),
        (_generated(content=""), "empty"),
    ],
)
def test_should_reject_invalid_generated_refactor_without_mutation(
    tmp_path: Path,
    generated: GeneratedAutomatedRefactor,
    message: str,
) -> None:
    session = _workspace(tmp_path)
    source = tmp_path / "src" / "export.ts"
    before_source = source.read_text()
    before_state = (session / "state.json").read_text()
    runner = SequenceTestRunner((PASS, SUITE_PASS))

    with pytest.raises(AutomatedRefactorError, match=message):
        apply_active_automated_refactor(
            tmp_path,
            StaticGenerator(generated),
            runner,
        )

    assert source.read_text() == before_source
    assert (session / "state.json").read_text() == before_state
    assert runner.calls == []


@pytest.mark.parametrize(
    "results",
    [
        (TestCommandProcessResult(1, "failed", ""),),
        (PASS, TestCommandProcessResult(1, "regression", "")),
    ],
)
def test_should_restore_source_and_state_when_verification_fails(
    tmp_path: Path,
    results: Tuple[TestCommandProcessResult, ...],
) -> None:
    session = _workspace(tmp_path)
    source = tmp_path / "src" / "export.ts"
    before_source = source.read_text()
    before_state = (session / "state.json").read_text()

    with pytest.raises(AutomatedRefactorError, match="verification failed"):
        apply_active_automated_refactor(
            tmp_path,
            StaticGenerator(_generated()),
            SequenceTestRunner(results),
        )

    assert source.read_text() == before_source
    assert (session / "state.json").read_text() == before_state


def test_should_exchange_strict_json_refactor(tmp_path: Path) -> None:
    _workspace(tmp_path)
    request = load_automated_refactor_request(tmp_path, "feature-1")
    runner = JsonProcessRunner(
        {
            "file_path": "src/export.ts",
            "content": REFACTORED_CONTENT,
            "summary": "Named the report value.",
        }
    )
    generator = JsonCommandAutomatedRefactorGenerator(
        CommandAnalyzerConfig(("reviewer",), 17.0, "json-command"),
        runner,
    )

    generated = generator.generate(request)

    assert generated.content == REFACTORED_CONTENT
    payload = json.loads(runner.calls[0][1])
    assert set(payload) == {
        "prompt_version",
        "prompt",
        "completion_sha256",
        "review_sha256",
        "review",
        "source",
    }
    assert runner.calls[0][0] == ("reviewer",)
    assert runner.calls[0][2] == 17.0


def test_should_run_codex_refactor_in_external_workspace(tmp_path: Path) -> None:
    _workspace(tmp_path)
    runner = CodexProcessRunner(
        {
            "file_path": "src/export.ts",
            "content": REFACTORED_CONTENT,
            "summary": "Named the report value.",
        }
    )
    generator = CodexExecAutomatedRefactorGenerator(
        CommandAnalyzerConfig(("codex",), 12.0, "codex-exec"),
        runner,
        tmp_path,
        command_resolver=FixedResolver(),
    )

    generated = generator.generate(
        load_automated_refactor_request(tmp_path, "feature-1")
    )

    assert generated.content == REFACTORED_CONTENT
    assert runner.workspace is not None
    assert runner.workspace != tmp_path
    assert not runner.workspace.exists()


def test_should_redact_provider_failure_payload(tmp_path: Path) -> None:
    _workspace(tmp_path)
    request = load_automated_refactor_request(tmp_path, "feature-1")
    generator = JsonCommandAutomatedRefactorGenerator(
        CommandAnalyzerConfig(("provider",), 12.0),
        FailingProcessRunner(),
    )

    with pytest.raises(AutomatedRefactorError) as captured:
        generator.generate(request)

    assert request.source.content not in str(captured.value)
    assert request.review not in str(captured.value)


def test_should_preserve_preexisting_atomic_collision(tmp_path: Path) -> None:
    session = _workspace(tmp_path)
    collision = session / ".state.json.automated-refactor.tmp"
    collision.write_text("owned", encoding="utf-8")
    source = tmp_path / "src" / "export.ts"
    before = source.read_text()

    with pytest.raises(AutomatedRefactorError, match="already in progress"):
        apply_active_automated_refactor(
            tmp_path,
            StaticGenerator(_generated()),
            SequenceTestRunner((PASS, SUITE_PASS)),
        )

    assert collision.read_text() == "owned"
    assert source.read_text() == before
    assert not (source.parent / ".export.ts.agent-refactor.tmp").exists()


@pytest.mark.parametrize(
    ("response", "message"),
    [
        ({"file_path": "src/export.ts"}, "keys"),
        (
            {
                "file_path": "src/export.ts",
                "content": 7,
                "summary": "Named the report value.",
            },
            "type",
        ),
        (
            {
                "file_path": "src/other.ts",
                "content": REFACTORED_CONTENT,
                "summary": "Named the report value.",
            },
            "exact final production",
        ),
    ],
)
def test_should_reject_invalid_json_provider_result(
    tmp_path: Path,
    response: dict[str, object],
    message: str,
) -> None:
    _workspace(tmp_path)
    generator = JsonCommandAutomatedRefactorGenerator(
        CommandAnalyzerConfig(("provider",), 12.0),
        JsonProcessRunner(response),
    )

    with pytest.raises(AutomatedRefactorError, match=message):
        generator.generate(load_automated_refactor_request(tmp_path, "feature-1"))


@pytest.mark.parametrize(
    ("generated", "message"),
    [
        (_generated(content="changed\0"), "null byte"),
        (_generated(content="x" * 1_000_001), "too large"),
        (
            GeneratedAutomatedRefactor(
                "src/export.ts",
                REFACTORED_CONTENT,
                "token=credential",
            ),
            "summary",
        ),
    ],
)
def test_should_reject_unsafe_generated_content(
    tmp_path: Path,
    generated: GeneratedAutomatedRefactor,
    message: str,
) -> None:
    _workspace(tmp_path)

    with pytest.raises(AutomatedRefactorError, match=message):
        apply_active_automated_refactor(
            tmp_path,
            StaticGenerator(generated),
            SequenceTestRunner((PASS, SUITE_PASS)),
        )


def test_should_require_approved_semantic_review(tmp_path: Path) -> None:
    create_refactor_workspace(tmp_path)

    with pytest.raises(AutomatedRefactorError, match="semantic review"):
        load_automated_refactor_request(tmp_path, "feature-1")


@pytest.mark.parametrize(("returncode", "message"), [(9, "exit code"), (0, "read")])
def test_should_fail_safely_when_codex_has_no_output(
    tmp_path: Path,
    returncode: int,
    message: str,
) -> None:
    _workspace(tmp_path)
    generator = CodexExecAutomatedRefactorGenerator(
        CommandAnalyzerConfig(("codex",), 12.0, "codex-exec"),
        MissingCodexOutputRunner(returncode),
        tmp_path,
        command_resolver=FixedResolver(),
    )

    with pytest.raises(AutomatedRefactorError, match=message):
        generator.generate(load_automated_refactor_request(tmp_path, "feature-1"))


def test_should_reject_invalid_public_contract_types(tmp_path: Path) -> None:
    _workspace(tmp_path)
    request = load_automated_refactor_request(tmp_path, "feature-1")

    with pytest.raises(ValueError, match="request"):
        validate_generated_automated_refactor(
            cast(AutomatedRefactorRequest, object()),
            _generated(),
        )
    with pytest.raises(ValueError, match="result"):
        validate_generated_automated_refactor(
            request,
            cast(GeneratedAutomatedRefactor, object()),
        )


def test_should_reject_invalid_json_and_codex_command(tmp_path: Path) -> None:
    _workspace(tmp_path)
    request = load_automated_refactor_request(tmp_path, "feature-1")

    with pytest.raises(AutomatedRefactorError, match="invalid JSON"):
        JsonCommandAutomatedRefactorGenerator(
            CommandAnalyzerConfig(("provider",), 12.0),
            RawProcessRunner(),
        ).generate(request)
    with pytest.raises(ValueError, match="one executable"):
        CodexExecAutomatedRefactorGenerator(
            CommandAnalyzerConfig(("codex", "extra"), 12.0, "codex-exec"),
            MissingCodexOutputRunner(0),
            tmp_path,
            command_resolver=FixedResolver(),
        )


def test_should_reject_concurrent_state_change(tmp_path: Path) -> None:
    session = _workspace(tmp_path)

    with pytest.raises(AutomatedRefactorError, match="concurrently"):
        apply_active_automated_refactor(
            tmp_path,
            MutatingGenerator(_generated(), session / "state.json"),
            SequenceTestRunner((PASS, SUITE_PASS)),
        )


def test_should_reject_missing_active_session(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "project.yml").write_text("name: reports\n", encoding="utf-8")

    with pytest.raises(AutomatedRefactorError, match="no active Session"):
        apply_active_automated_refactor(
            tmp_path,
            StaticGenerator(_generated()),
            SequenceTestRunner((PASS, SUITE_PASS)),
        )


def test_should_run_automated_refactor_cli(tmp_path: Path) -> None:
    _workspace(tmp_path)
    output = io.StringIO()
    process_runner = JsonProcessRunner(
        {
            "file_path": "src/export.ts",
            "content": REFACTORED_CONTENT,
            "summary": "Named the report value.",
        }
    )

    exit_code = main(
        ["refactor", "automated"],
        out=output,
        root=tmp_path,
        runner=process_runner,
        test_runner=SequenceTestRunner((PASS, SUITE_PASS)),
    )

    assert exit_code == 0
    assert output.getvalue() == (
        "Automated refactor complete: feature-1 (src/export.ts; tests verified; DONE)\n"
    )


def test_should_keep_schema_json_serializable() -> None:
    assert (
        json.loads(json.dumps(AUTOMATED_REFACTOR_SCHEMA))["additionalProperties"]
        is False
    )
