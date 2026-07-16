import hashlib
import io
import json
from pathlib import Path

import pytest

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.implementation_review import (
    ImplementationReviewError,
    run_active_implementation_review,
)
from tests.implementation_review_support import create_review_workspace


def test_should_record_digest_bound_completion_snapshot(tmp_path: Path) -> None:
    session = create_review_workspace(tmp_path)
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))

    assert state["implementation_completion"] == {
        "completed_tests": ["TC1"],
        "final_test": "TC1",
        "green_evidence_sha256": hashlib.sha256(
            json.dumps(
                state["green_evidence"],
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest(),
        "test_source_sha256": state["test_source"]["sha256"],
        "production_source_sha256": state["production_source"]["sha256"],
    }


def test_should_generate_invariant_report_and_enter_refactor(tmp_path: Path) -> None:
    session = create_review_workspace(tmp_path)

    run = run_active_implementation_review(tmp_path)

    report = (session / "review.md").read_text(encoding="utf-8")
    assert run.session_id == "feature-1"
    assert run.final_test_id == "TC1"
    assert run.completed_test_count == 1
    assert report.startswith("# Implementation Review\n")
    assert "Audit integrity: passed" in report
    assert "Semantic automated review: deferred to v0.3" in report
    assert "all tests passed" not in report
    assert "export function" not in report
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["state"] == "REFACTOR"
    assert state["implementation_review"] == {
        "decision": "invariant_review_passed",
        "completion_sha256": run.completion_sha256,
        "report_sha256": hashlib.sha256(report.encode()).hexdigest(),
    }


def test_should_render_deterministic_review_cli_output(tmp_path: Path) -> None:
    create_review_workspace(tmp_path)
    output = io.StringIO()

    exit_code = main(["review"], out=output, root=tmp_path)

    assert exit_code == 0
    assert output.getvalue() == (
        "Implementation review passed: feature-1 "
        "(1 tests; final TC1; ready for REFACTOR)\n"
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("missing", None),
        ("extra", True),
        ("completed_tests", ["TC2"]),
        ("final_test", "TC2"),
        ("green_evidence_sha256", "0" * 64),
        ("test_source_sha256", "0" * 64),
        ("production_source_sha256", "0" * 64),
    ],
)
def test_should_reject_invalid_completion_snapshot_without_mutation(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    session = create_review_workspace(tmp_path)
    state_path = session / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    completion = state["implementation_completion"]
    if field == "missing":
        state.pop("implementation_completion")
    elif field == "extra":
        completion["unexpected"] = value
    else:
        completion[field] = value
    state_path.write_text(json.dumps(state), encoding="utf-8")
    before = state_path.read_text(encoding="utf-8")

    with pytest.raises(ImplementationReviewError, match="completion"):
        run_active_implementation_review(tmp_path)

    assert state_path.read_text(encoding="utf-8") == before
    assert (session / "review.md").read_text(encoding="utf-8").startswith("# Review")


def test_should_reject_green_evidence_changed_after_completion(
    tmp_path: Path,
) -> None:
    session = create_review_workspace(tmp_path)
    state_path = session / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["green_evidence"]["full_suite"]["stdout"] = "changed"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    before = state_path.read_text(encoding="utf-8")

    with pytest.raises(ImplementationReviewError, match="completion"):
        run_active_implementation_review(tmp_path)

    assert state_path.read_text(encoding="utf-8") == before


@pytest.mark.parametrize(
    "filename",
    ["review.md", ".review.md.review.tmp", ".state.json.review.tmp"],
)
def test_should_reject_unsafe_or_colliding_review_artifact(
    tmp_path: Path,
    filename: str,
) -> None:
    session = create_review_workspace(tmp_path)
    state_path = session / "state.json"
    before = state_path.read_text(encoding="utf-8")
    path = session / filename
    if filename == "review.md":
        replacement = tmp_path / "replacement.md"
        replacement.write_text("safe\n", encoding="utf-8")
        path.unlink()
        path.symlink_to(replacement)
    else:
        path.write_text("busy\n", encoding="utf-8")

    with pytest.raises(ImplementationReviewError):
        run_active_implementation_review(tmp_path)

    assert state_path.read_text(encoding="utf-8") == before
    if filename != "review.md":
        assert path.read_text(encoding="utf-8") == "busy\n"


def test_should_reject_user_edited_review_without_overwrite(tmp_path: Path) -> None:
    session = create_review_workspace(tmp_path)
    review_path = session / "review.md"
    review_path.write_text("# My review\n\nKeep this.\n", encoding="utf-8")

    with pytest.raises(ImplementationReviewError, match="unrecognized"):
        run_active_implementation_review(tmp_path)

    assert review_path.read_text(encoding="utf-8") == "# My review\n\nKeep this.\n"


def test_should_reject_non_review_state_without_mutation(tmp_path: Path) -> None:
    session = create_review_workspace(tmp_path)
    run_active_implementation_review(tmp_path)
    state_path = session / "state.json"
    before = state_path.read_text(encoding="utf-8")

    with pytest.raises(ImplementationReviewError, match="REVIEW"):
        run_active_implementation_review(tmp_path)

    assert state_path.read_text(encoding="utf-8") == before


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("session_id", "other"),
        ("progress_extra", True),
        ("progress_phase", "RED"),
    ],
)
def test_should_reject_stale_review_state(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    session = create_review_workspace(tmp_path)
    state_path = session / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if field == "session_id":
        state["session_id"] = value
    elif field == "progress_extra":
        state["tdd_cycle"]["unexpected"] = value
    else:
        state["tdd_cycle"]["phase"] = value
    state_path.write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(ImplementationReviewError):
        run_active_implementation_review(tmp_path)


@pytest.mark.parametrize("content", [None, "x" * 20_001])
def test_should_reject_missing_or_oversized_review_artifact(
    tmp_path: Path,
    content: object,
) -> None:
    session = create_review_workspace(tmp_path)
    review_path = session / "review.md"
    if content is None:
        review_path.unlink()
    else:
        assert isinstance(content, str)
        review_path.write_text(content, encoding="utf-8")

    with pytest.raises(ImplementationReviewError, match="Review artifact"):
        run_active_implementation_review(tmp_path)


def test_should_reject_missing_active_session(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "project.yml").write_text("name: reports\n", encoding="utf-8")

    with pytest.raises(ImplementationReviewError, match="no active Session"):
        run_active_implementation_review(tmp_path)


def test_should_translate_unreadable_project_status(tmp_path: Path) -> None:
    with pytest.raises(ImplementationReviewError, match="status could not be read"):
        run_active_implementation_review(tmp_path)
