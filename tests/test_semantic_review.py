import hashlib
import io
import json
from pathlib import Path
from typing import Optional

import pytest

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.implementation_review import (
    ImplementationReviewError,
    run_active_implementation_review,
)
from sdd_tdd_agent.model_adapter import CommandAnalyzerConfig, ProcessResult
from sdd_tdd_agent.semantic_review import (
    GeneratedSemanticReview,
    SemanticFinding,
    SemanticReviewError,
    SemanticReviewRequest,
    load_semantic_review_request,
    run_semantic_review,
    validate_generated_semantic_review,
)
from sdd_tdd_agent.semantic_review_adapter import (
    CodexExecSemanticReviewer,
    JsonCommandSemanticReviewer,
)
from tests.implementation_review_support import create_review_workspace


def _finding(
    *,
    severity: str = "warning",
    file_path: str = "src/export.ts",
    line: int = 1,
) -> SemanticFinding:
    return SemanticFinding(
        finding_id="SR1",
        area="readability",
        severity=severity,
        file_path=file_path,
        line=line,
        message="The export name hides its intent.",
        recommendation="Use a domain-specific helper name.",
    )


def _review(
    *,
    decision: str = "approved",
    findings: tuple[SemanticFinding, ...] = (_finding(),),
) -> GeneratedSemanticReview:
    return GeneratedSemanticReview(
        summary="The implementation is safe with one readability note.",
        findings=findings,
        decision=decision,
    )


class FixedReviewer:
    def __init__(self, review: GeneratedSemanticReview) -> None:
        self.generated = review
        self.request: Optional[SemanticReviewRequest] = None

    def review(self, request: SemanticReviewRequest) -> GeneratedSemanticReview:
        self.request = request
        return self.generated


class JsonRunner:
    def __init__(
        self,
        payload: dict[str, object],
        returncode: int = 0,
    ) -> None:
        self.payload = payload
        self.returncode = returncode
        self.stdin = ""

    def run(
        self,
        command: tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.stdin = stdin
        return ProcessResult(self.returncode, json.dumps(self.payload), "SECRET")


class CodexRunner:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.workspace: Optional[Path] = None

    def run(
        self,
        command: tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.workspace = Path(command[command.index("--cd") + 1])
        output = Path(command[command.index("--output-last-message") + 1])
        output.write_text(json.dumps(self.payload), encoding="utf-8")
        return ProcessResult(0, "", "")


class FixedResolver:
    def resolve(self, executable: str) -> str:
        return "resolved-codex"


def _payload(review: GeneratedSemanticReview) -> dict[str, object]:
    return {
        "summary": review.summary,
        "findings": [
            {
                "finding_id": finding.finding_id,
                "area": finding.area,
                "severity": finding.severity,
                "file_path": finding.file_path,
                "line": finding.line,
                "message": finding.message,
                "recommendation": finding.recommendation,
            }
            for finding in review.findings
        ],
        "decision": review.decision,
    }


def test_should_load_digest_bound_isolated_semantic_review_context(
    tmp_path: Path,
) -> None:
    create_review_workspace(tmp_path)

    request = load_semantic_review_request(tmp_path, "feature-1")

    assert request.prompt_version == "v1"
    assert request.final_test_id == "TC1"
    assert len(request.completion_sha256) == 64
    assert tuple(source.path for source in request.sources) == (
        "src/export.test.ts",
        "src/export.ts",
    )
    serialized = json.dumps(request.__dict__, default=lambda value: value.__dict__)
    for forbidden in (
        "REQUIREMENT-SENTINEL",
        "DESIGN-SENTINEL",
        "TASK-SENTINEL",
        "all tests passed",
        "green_evidence",
        "raw_state",
    ):
        assert forbidden not in serialized


def test_should_record_approved_semantic_review_then_enter_refactor(
    tmp_path: Path,
) -> None:
    session = create_review_workspace(tmp_path)
    reviewer = FixedReviewer(_review())

    run = run_semantic_review(tmp_path, "feature-1", reviewer)

    assert run.decision == "approved"
    report = (session / "review.md").read_text(encoding="utf-8")
    assert "# Semantic Implementation Review" in report
    assert "readability" in report
    assert "export function" not in report
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["state"] == "REVIEW"
    assert (
        state["semantic_review"]["report_sha256"]
        == hashlib.sha256(report.encode()).hexdigest()
    )

    invariant = run_active_implementation_review(tmp_path)

    assert invariant.report_sha256 == state["semantic_review"]["report_sha256"]
    final_state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert final_state["state"] == "REFACTOR"
    assert final_state["implementation_review"]["decision"] == (
        "semantic_review_passed"
    )


def test_should_keep_required_changes_in_review(tmp_path: Path) -> None:
    session = create_review_workspace(tmp_path)
    review = _review(
        decision="changes_required",
        findings=(_finding(severity="error"),),
    )

    run_semantic_review(tmp_path, "feature-1", FixedReviewer(review))

    before = (session / "state.json").read_text(encoding="utf-8")
    with pytest.raises(ImplementationReviewError, match="changes"):
        run_active_implementation_review(tmp_path)
    assert (session / "state.json").read_text(encoding="utf-8") == before


@pytest.mark.parametrize(
    "review",
    [
        _review(decision="approved", findings=(_finding(severity="error"),)),
        _review(findings=(_finding(file_path="src/other.ts"),)),
        _review(findings=(_finding(line=999),)),
        _review(findings=(_finding(), _finding())),
    ],
)
def test_should_reject_invalid_semantic_result_without_mutation(
    tmp_path: Path,
    review: GeneratedSemanticReview,
) -> None:
    session = create_review_workspace(tmp_path)
    request = load_semantic_review_request(tmp_path, "feature-1")
    before_state = (session / "state.json").read_text(encoding="utf-8")
    before_report = (session / "review.md").read_text(encoding="utf-8")

    with pytest.raises(ValueError):
        validate_generated_semantic_review(request, review)

    assert (session / "state.json").read_text(encoding="utf-8") == before_state
    assert (session / "review.md").read_text(encoding="utf-8") == before_report


def test_should_exchange_strict_semantic_json_payload(tmp_path: Path) -> None:
    create_review_workspace(tmp_path)
    runner = JsonRunner(_payload(_review()))
    reviewer = JsonCommandSemanticReviewer(
        CommandAnalyzerConfig(("provider",), 12.0),
        runner,
    )

    generated = reviewer.review(load_semantic_review_request(tmp_path, "feature-1"))

    assert generated == _review()
    payload = json.loads(runner.stdin)
    assert set(payload) == {
        "prompt_version",
        "prompt",
        "completion_sha256",
        "final_test_id",
        "sources",
    }
    assert [source["path"] for source in payload["sources"]] == [
        "src/export.test.ts",
        "src/export.ts",
    ]


def test_should_run_semantic_review_from_cli(tmp_path: Path) -> None:
    create_review_workspace(tmp_path)
    output = io.StringIO()

    exit_code = main(
        ["review", "semantic"],
        out=output,
        root=tmp_path,
        runner=JsonRunner(_payload(_review())),
    )

    assert exit_code == 0
    assert output.getvalue() == (
        "Semantic review ready: feature-1 (approved; 1 findings; REVIEW)\n"
    )


def test_should_run_codex_semantic_review_in_external_workspace(
    tmp_path: Path,
) -> None:
    create_review_workspace(tmp_path)
    runner = CodexRunner(_payload(_review()))
    reviewer = CodexExecSemanticReviewer(
        CommandAnalyzerConfig(("codex",), 12.0, "codex-exec"),
        runner,
        tmp_path,
        command_resolver=FixedResolver(),
    )

    generated = reviewer.review(load_semantic_review_request(tmp_path, "feature-1"))

    assert generated == _review()
    assert runner.workspace is not None
    assert runner.workspace != tmp_path
    assert not runner.workspace.exists()


def test_should_translate_semantic_provider_validation_error(tmp_path: Path) -> None:
    create_review_workspace(tmp_path)
    runner = JsonRunner({"summary": "missing fields"})

    with pytest.raises(SemanticReviewError):
        JsonCommandSemanticReviewer(
            CommandAnalyzerConfig(("provider",), 12.0),
            runner,
        ).review(load_semantic_review_request(tmp_path, "feature-1"))


def test_should_reject_source_copy_in_semantic_output(tmp_path: Path) -> None:
    create_review_workspace(tmp_path)
    request = load_semantic_review_request(tmp_path, "feature-1")
    review = GeneratedSemanticReview(
        summary="export function exportReport(): string {",
        findings=(),
        decision="approved",
    )

    with pytest.raises(ValueError, match="copy source"):
        validate_generated_semantic_review(request, review)


@pytest.mark.parametrize(
    "temporary_name",
    [".review.md.semantic.tmp", ".state.json.semantic-review.tmp"],
)
def test_should_preserve_semantic_update_collision(
    tmp_path: Path,
    temporary_name: str,
) -> None:
    session = create_review_workspace(tmp_path)
    temporary = session / temporary_name
    temporary.write_text("occupied\n", encoding="utf-8")

    with pytest.raises(SemanticReviewError, match="already in progress"):
        run_semantic_review(tmp_path, "feature-1", FixedReviewer(_review()))

    assert temporary.read_text(encoding="utf-8") == "occupied\n"


def test_should_redact_semantic_provider_failure_content(tmp_path: Path) -> None:
    create_review_workspace(tmp_path)
    reviewer = JsonCommandSemanticReviewer(
        CommandAnalyzerConfig(("provider", "SECRET"), 12.0),
        JsonRunner({"source": "SECRET"}, returncode=9),
    )

    with pytest.raises(SemanticReviewError) as captured:
        reviewer.review(load_semantic_review_request(tmp_path, "feature-1"))

    assert str(captured.value) == "Semantic reviewer failed with exit code 9"
    assert "SECRET" not in str(captured.value)
