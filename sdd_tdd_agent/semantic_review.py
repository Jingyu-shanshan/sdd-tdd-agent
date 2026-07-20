import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import ClassVar, Protocol, Set, Tuple

from sdd_tdd_agent.implementation_review import (
    PENDING_REVIEW,
    ImplementationReviewError,
    _load_context,
)
from sdd_tdd_agent.refactor_completion import (
    RefactorVerificationError,
    _validate_artifacts,
)
from sdd_tdd_agent.tdd_cycle import SourceSnapshot


PROMPT_VERSION = "v1"
PROMPT_PATH = (
    Path(__file__).parent / "prompts" / "semantic_review" / f"{PROMPT_VERSION}.md"
)
REVIEW_AREAS = {
    "clean_code",
    "solid",
    "duplication",
    "complexity",
    "readability",
    "bug",
    "performance",
    "security",
}
REVIEW_SEVERITIES = {"info", "warning", "error"}
REVIEW_DECISIONS = {"approved", "changes_required"}
MAX_REVIEW_SOURCE_BYTES = 1_000_000
MAX_REVIEW_TEXT_CHARACTERS = 4_000
MAX_REVIEW_FINDINGS = 100
MAX_REVIEW_REPORT_CHARACTERS = 20_000
FINDING_ID_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
SENSITIVE_OUTPUT_PATTERN = re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]")


class SemanticReviewError(RuntimeError):
    """Safe public error for semantic review generation and persistence."""


@dataclass(frozen=True)
class SemanticReviewRequest:
    """Digest-bound source-only context for one semantic implementation review."""

    __test__: ClassVar[bool] = False

    prompt_version: str
    prompt: str
    completion_sha256: str
    final_test_id: str
    sources: Tuple[SourceSnapshot, ...]


@dataclass(frozen=True)
class SemanticFinding:
    """One typed semantic code-review finding."""

    finding_id: str
    area: str
    severity: str
    file_path: str
    line: int
    message: str
    recommendation: str


@dataclass(frozen=True)
class GeneratedSemanticReview:
    """One complete typed semantic review generated from bounded source."""

    summary: str
    findings: Tuple[SemanticFinding, ...]
    decision: str


class SemanticReviewer(Protocol):
    """Typed and mockable model boundary for semantic review."""

    def review(self, request: SemanticReviewRequest) -> GeneratedSemanticReview:
        """Review only the supplied digest-bound sources."""
        ...


@dataclass(frozen=True)
class SemanticReviewRun:
    """Result of persisting one semantic review while retaining REVIEW state."""

    __test__: ClassVar[bool] = False

    session_id: str
    decision: str
    finding_count: int
    report_sha256: str


def _artifact_path(value: object, label: str) -> str:
    if not isinstance(value, dict):
        raise SemanticReviewError(f"{label} artifact is invalid")
    file_path = value.get("file_path")
    if not isinstance(file_path, str):
        raise SemanticReviewError(f"{label} artifact is invalid")
    return file_path


def _read_source(root: Path, file_path: str, label: str) -> SourceSnapshot:
    path = PurePosixPath(file_path.replace("\\", "/"))
    if (
        file_path != path.as_posix()
        or path.is_absolute()
        or not path.parts
        or ".." in path.parts
        or path.parts[0] in {".agent", ".git"}
    ):
        raise SemanticReviewError(f"{label} artifact path is unsafe")
    target = root.resolve()
    for part in path.parts:
        target = target / part
        if target.is_symlink():
            raise SemanticReviewError(f"{label} artifact changed")
    try:
        content = target.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise SemanticReviewError(f"{label} artifact could not be read") from error
    if not content.strip() or len(content.encode("utf-8")) > MAX_REVIEW_SOURCE_BYTES:
        raise SemanticReviewError(f"{label} artifact is invalid")
    return SourceSnapshot(path.as_posix(), content)


def _validated_context(root: Path, session_id: str):
    try:
        context = _load_context(root, session_id)
    except ImplementationReviewError as error:
        raise SemanticReviewError(str(error)) from error
    completion = context.state.get("implementation_completion")
    if not isinstance(completion, dict):
        raise SemanticReviewError("Implementation completion is invalid")
    try:
        _validate_artifacts(
            root,
            context.state,
            context.final_test_id,
            completion,
        )
    except RefactorVerificationError as error:
        raise SemanticReviewError(str(error)) from error
    return context


def load_semantic_review_request(
    root: Path,
    session_id: str,
) -> SemanticReviewRequest:
    """Load one source-only semantic review request from a completed plan."""
    context = _validated_context(root, session_id)
    test_path = _artifact_path(context.state.get("test_source"), "Final test")
    production_path = _artifact_path(
        context.state.get("production_source"),
        "Final production",
    )
    sources = (
        _read_source(root, test_path, "Final test"),
        _read_source(root, production_path, "Final production"),
    )
    return SemanticReviewRequest(
        PROMPT_VERSION,
        PROMPT_PATH.read_text(encoding="utf-8"),
        context.completion_sha256,
        context.final_test_id,
        sources,
    )


def _review_text(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > MAX_REVIEW_TEXT_CHARACTERS
        or "\0" in value
        or SENSITIVE_OUTPUT_PATTERN.search(value) is not None
    ):
        raise ValueError(f"Semantic review {label} is invalid")
    return value


def validate_generated_semantic_review(
    request: SemanticReviewRequest,
    generated: GeneratedSemanticReview,
) -> GeneratedSemanticReview:
    """Validate one semantic review against its exact visible source context."""
    if not isinstance(request, SemanticReviewRequest):
        raise ValueError("Semantic review request is invalid")
    if not isinstance(generated, GeneratedSemanticReview):
        raise ValueError("Semantic review result is invalid")
    _review_text(generated.summary, "summary")
    if not isinstance(generated.findings, tuple):
        raise ValueError("Semantic review findings must be a tuple")
    if len(generated.findings) > MAX_REVIEW_FINDINGS:
        raise ValueError("Semantic review contains too many findings")
    if generated.decision not in REVIEW_DECISIONS:
        raise ValueError("Semantic review decision is invalid")
    sources = {source.path: source for source in request.sources}
    finding_ids: Set[str] = set()
    locations: Set[Tuple[str, int, str]] = set()
    error_count = 0
    for finding in generated.findings:
        if not isinstance(finding, SemanticFinding):
            raise ValueError("Semantic review finding is invalid")
        source = sources.get(finding.file_path)
        location = (finding.file_path, finding.line, finding.area)
        if (
            FINDING_ID_PATTERN.fullmatch(finding.finding_id) is None
            or finding.finding_id in finding_ids
            or finding.area not in REVIEW_AREAS
            or finding.severity not in REVIEW_SEVERITIES
            or source is None
            or isinstance(finding.line, bool)
            or not isinstance(finding.line, int)
            or finding.line <= 0
            or finding.line > len(source.content.splitlines())
            or location in locations
        ):
            raise ValueError("Semantic review finding is invalid")
        _review_text(finding.message, "message")
        _review_text(finding.recommendation, "recommendation")
        finding_ids.add(finding.finding_id)
        locations.add(location)
        if finding.severity == "error":
            error_count += 1
    if generated.decision == "approved" and error_count:
        raise ValueError("Approved semantic review contains errors")
    if generated.decision == "changes_required" and not generated.findings:
        raise ValueError("Required semantic changes need at least one finding")
    output_text = "\n".join(
        (
            generated.summary,
            *(finding.message for finding in generated.findings),
            *(finding.recommendation for finding in generated.findings),
        )
    )
    for source in request.sources:
        if any(
            len(line.strip()) >= 24 and line.strip() in output_text
            for line in source.content.splitlines()
        ):
            raise ValueError("Semantic review must not copy source content")
    return generated


def _render_review(
    request: SemanticReviewRequest,
    generated: GeneratedSemanticReview,
) -> str:
    lines = [
        "# Semantic Implementation Review",
        "",
        "## Result",
        "",
        f"- Decision: `{generated.decision}`",
        f"- Final test: `{request.final_test_id}`",
        f"- Completion snapshot: `{request.completion_sha256}`",
        f"- Findings: {len(generated.findings)}",
        "",
        "## Summary",
        "",
        generated.summary,
        "",
        "## Findings",
        "",
    ]
    if not generated.findings:
        lines.append("- None identified.")
    for finding in generated.findings:
        lines.extend(
            (
                f"### {finding.finding_id}: {finding.area}",
                "",
                f"- Severity: `{finding.severity}`",
                f"- Location: `{finding.file_path}:{finding.line}`",
                f"- Finding: {finding.message}",
                f"- Recommendation: {finding.recommendation}",
                "",
            )
        )
    lines.extend(
        (
            "## Scope",
            "",
            "- Reviewed only the digest-bound final test and production source.",
            "- Source code and process output are not copied into this report.",
            "- Deterministic integrity review is still required before REFACTOR.",
            "",
        )
    )
    return "\n".join(lines)


def _write_review(context, generated: GeneratedSemanticReview, report: str) -> str:
    if context.raw_review != PENDING_REVIEW or "semantic_review" in context.state:
        raise SemanticReviewError("Semantic review has already been recorded")
    if len(report) > MAX_REVIEW_REPORT_CHARACTERS:
        raise SemanticReviewError("Semantic review report is too large")
    report_sha = hashlib.sha256(report.encode("utf-8")).hexdigest()
    context.state["semantic_review"] = {
        "decision": generated.decision,
        "completion_sha256": context.completion_sha256,
        "report_sha256": report_sha,
        "finding_count": len(generated.findings),
        "error_count": sum(
            finding.severity == "error" for finding in generated.findings
        ),
    }
    review_temporary = context.review_path.with_name(".review.md.semantic.tmp")
    state_temporary = context.state_path.with_name(".state.json.semantic-review.tmp")
    review_temporary_created = False
    state_temporary_created = False
    try:
        with review_temporary.open("x", encoding="utf-8") as stream:
            stream.write(report)
        review_temporary_created = True
        with state_temporary.open("x", encoding="utf-8") as stream:
            stream.write(f"{json.dumps(context.state, indent=2)}\n")
        state_temporary_created = True
        if (
            context.state_path.read_text(encoding="utf-8") != context.raw_state
            or context.review_path.read_text(encoding="utf-8") != context.raw_review
        ):
            raise SemanticReviewError("Semantic review inputs changed concurrently")
        review_temporary.replace(context.review_path)
        state_temporary.replace(context.state_path)
    except FileExistsError as error:
        raise SemanticReviewError(
            "Semantic review update is already in progress"
        ) from error
    except OSError as error:
        raise SemanticReviewError("Semantic review could not be recorded") from error
    finally:
        created_temporaries = (
            (review_temporary, review_temporary_created),
            (state_temporary, state_temporary_created),
        )
        for temporary, was_created in created_temporaries:
            if was_created and temporary.exists():
                temporary.unlink()
    return report_sha


def run_semantic_review(
    root: Path,
    session_id: str,
    reviewer: SemanticReviewer,
) -> SemanticReviewRun:
    """Generate and atomically record one active semantic review."""
    before = _validated_context(root, session_id)
    request = load_semantic_review_request(root, session_id)
    generated = reviewer.review(request)
    validate_generated_semantic_review(request, generated)
    after = _validated_context(root, session_id)
    if after.raw_state != before.raw_state or after.raw_review != before.raw_review:
        raise SemanticReviewError("Semantic review inputs changed concurrently")
    report = _render_review(request, generated)
    report_sha = _write_review(after, generated, report)
    return SemanticReviewRun(
        session_id,
        generated.decision,
        len(generated.findings),
        report_sha,
    )
