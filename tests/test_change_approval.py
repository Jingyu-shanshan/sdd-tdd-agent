import json
from io import StringIO
from pathlib import Path

import pytest

from sdd_tdd_agent.change_approval import (
    ChangeApprovalError,
    ChangeRisk,
    ProjectChange,
    approve_active_change,
    assess_change_risk,
    load_active_change_approval,
    reject_active_change,
    render_change_approval,
    request_active_change_approval,
)
from sdd_tdd_agent.cli import main


def _workspace(root: Path, session_id: str = "feature-1") -> Path:
    workspace = root / ".agent"
    session = workspace / "sessions" / session_id
    session.mkdir(parents=True)
    (workspace / "project.yml").write_text(
        f"name: reports\ncurrent_session: {session_id}\n",
        encoding="utf-8",
    )
    (session / "state.json").write_text(
        json.dumps(
            {
                "session_id": session_id,
                "kind": "feature",
                "state": "DONE",
                "current_task": 1,
                "current_cycle": 1,
            }
        ),
        encoding="utf-8",
    )
    return session


def test_should_classify_low_medium_and_high_risk_changes() -> None:
    low = assess_change_risk(
        (
            ProjectChange("README.md", "modified"),
            ProjectChange("tests/test_report.py", "added"),
        )
    )
    medium = assess_change_risk((ProjectChange("src/report.py", "modified"),))
    high = assess_change_risk((ProjectChange("pyproject.toml", "modified"),))
    deletion = assess_change_risk((ProjectChange("docs/old.md", "deleted"),))
    control = assess_change_risk(
        (ProjectChange(".github/workflows/ci.yml", "modified"),)
    )

    assert (low.level, low.requires_human_approval) == ("low", False)
    assert (medium.level, medium.requires_human_approval) == ("medium", True)
    assert (high.level, high.requires_human_approval) == ("high", True)
    assert deletion.level == "high"
    assert control.reasons == ("project control change",)


def test_should_make_risk_digest_independent_of_input_order() -> None:
    first = assess_change_risk(
        (
            ProjectChange("src/a.py", "modified"),
            ProjectChange("tests/test_a.py", "added"),
        )
    )
    second = assess_change_risk(tuple(reversed(first.changes)))

    assert first == second
    assert len(first.change_digest) == 64


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ((), "must not be empty"),
        ((ProjectChange("../secret", "modified"),), "relative path"),
        ((ProjectChange("/secret", "modified"),), "relative path"),
        ((ProjectChange("src\\secret.py", "modified"),), "relative path"),
        ((ProjectChange("src/a.py", "renamed"),), "change kind"),
        (
            (
                ProjectChange("src/a.py", "added"),
                ProjectChange("src/a.py", "modified"),
            ),
            "unique",
        ),
    ],
)
def test_should_reject_invalid_change_sets(
    changes: tuple[ProjectChange, ...],
    message: str,
) -> None:
    with pytest.raises(ChangeApprovalError, match=message):
        assess_change_risk(changes)


def test_should_request_and_approve_digest_bound_change(tmp_path: Path) -> None:
    session = _workspace(tmp_path)
    risk = assess_change_risk((ProjectChange("src/report.py", "modified"),))

    pending = request_active_change_approval(tmp_path, risk)
    approved = approve_active_change(tmp_path)

    assert pending.decision == "pending"
    assert approved.decision == "approved"
    assert approved.change_digest == risk.change_digest
    payload = json.loads((session / "change-approval.json").read_text(encoding="utf-8"))
    assert payload == {
        "schema_version": 1,
        "session_id": "feature-1",
        "operation": "git_commit",
        "change_digest": risk.change_digest,
        "risk_level": "medium",
        "reasons": ["production change"],
        "decision": "approved",
    }


def test_should_record_low_risk_as_not_required(tmp_path: Path) -> None:
    _workspace(tmp_path)
    risk = assess_change_risk((ProjectChange("README.md", "modified"),))

    approval = request_active_change_approval(tmp_path, risk)

    assert approval.decision == "not_required"
    with pytest.raises(ChangeApprovalError, match="pending"):
        approve_active_change(tmp_path)


def test_should_reject_pending_change_with_normalized_reason(tmp_path: Path) -> None:
    _workspace(tmp_path)
    risk = assess_change_risk((ProjectChange("src/report.py", "modified"),))
    request_active_change_approval(tmp_path, risk)

    rejected = reject_active_change(tmp_path, "  Needs a migration plan.  ")

    assert rejected.decision == "rejected"
    assert rejected.reason == "Needs a migration plan."


def test_should_reuse_only_an_identical_existing_request(tmp_path: Path) -> None:
    _workspace(tmp_path)
    first = assess_change_risk((ProjectChange("src/report.py", "modified"),))
    second = assess_change_risk((ProjectChange("src/other.py", "modified"),))

    created = request_active_change_approval(tmp_path, first)

    assert request_active_change_approval(tmp_path, first) == created
    with pytest.raises(ChangeApprovalError, match="different change set"):
        request_active_change_approval(tmp_path, second)

    approve_active_change(tmp_path)
    assert request_active_change_approval(tmp_path, first).decision == "approved"


def test_should_reject_a_forged_risk_assessment(tmp_path: Path) -> None:
    _workspace(tmp_path)
    change = ProjectChange("src/report.py", "modified")
    forged = ChangeRisk((change,), "0" * 64, "low", ("production change",), False)

    with pytest.raises(ChangeApprovalError, match="assessment is invalid"):
        request_active_change_approval(tmp_path, forged)


def test_should_render_source_free_status_and_cli_decisions(tmp_path: Path) -> None:
    _workspace(tmp_path)
    risk = assess_change_risk((ProjectChange("src/report.py", "modified"),))
    request_active_change_approval(tmp_path, risk)
    output = StringIO()

    assert main(["approval", "status"], out=output, root=tmp_path) == 0
    assert output.getvalue() == render_change_approval(
        load_active_change_approval(tmp_path)
    )
    assert "src/report.py" not in output.getvalue()

    output = StringIO()
    assert main(["approval", "approve"], out=output, root=tmp_path) == 0
    assert output.getvalue() == "Change approved: feature-1 (medium)\n"


def test_should_reject_through_cli_and_require_reason(tmp_path: Path) -> None:
    _workspace(tmp_path)
    risk = assess_change_risk((ProjectChange("src/report.py", "modified"),))
    request_active_change_approval(tmp_path, risk)
    output = StringIO()
    errors = StringIO()

    assert (
        main(
            ["approval", "reject", "unsafe", "migration"],
            out=output,
            err=errors,
            root=tmp_path,
        )
        == 0
    )
    assert output.getvalue() == "Change rejected: feature-1 (medium)\n"


def test_should_reject_tampered_record_without_mutation(tmp_path: Path) -> None:
    session = _workspace(tmp_path)
    path = session / "change-approval.json"
    path.write_text('{"schema_version": 1}', encoding="utf-8")
    before = path.read_text(encoding="utf-8")

    with pytest.raises(ChangeApprovalError, match="invalid"):
        load_active_change_approval(tmp_path)

    assert path.read_text(encoding="utf-8") == before


@pytest.mark.parametrize(
    "content",
    [
        "[]",
        '{"schema_version": 1, "schema_version": 1}',
        "x" * 8_193,
    ],
)
def test_should_reject_invalid_record_encodings(
    tmp_path: Path,
    content: str,
) -> None:
    session = _workspace(tmp_path)
    (session / "change-approval.json").write_text(content, encoding="utf-8")

    with pytest.raises(ChangeApprovalError, match="invalid"):
        load_active_change_approval(tmp_path)


def test_should_reject_symlinked_approval_file(tmp_path: Path) -> None:
    session = _workspace(tmp_path)
    target = tmp_path / "outside.json"
    target.write_text("{}", encoding="utf-8")
    (session / "change-approval.json").symlink_to(target)

    with pytest.raises(ChangeApprovalError, match="regular file"):
        load_active_change_approval(tmp_path)


def test_should_preserve_preexisting_atomic_temporary_file(tmp_path: Path) -> None:
    session = _workspace(tmp_path)
    temporary = session / ".change-approval.json.tmp"
    temporary.write_text("owner", encoding="utf-8")
    risk = assess_change_risk((ProjectChange("src/report.py", "modified"),))

    with pytest.raises(ChangeApprovalError, match="update already in progress"):
        request_active_change_approval(tmp_path, risk)

    assert temporary.read_text(encoding="utf-8") == "owner"


def test_should_reject_record_for_another_active_session(tmp_path: Path) -> None:
    session = _workspace(tmp_path)
    risk = assess_change_risk((ProjectChange("src/report.py", "modified"),))
    request_active_change_approval(tmp_path, risk)
    payload = json.loads((session / "change-approval.json").read_text(encoding="utf-8"))
    payload["session_id"] = "another"
    (session / "change-approval.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(ChangeApprovalError, match="active Session"):
        load_active_change_approval(tmp_path)


def test_should_require_active_done_session(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "project.yml").write_text("name: reports\n", encoding="utf-8")

    with pytest.raises(ChangeApprovalError, match="no active Session"):
        load_active_change_approval(tmp_path)

    session = _workspace(tmp_path / "other")
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    state["state"] = "REVIEW"
    (session / "state.json").write_text(json.dumps(state), encoding="utf-8")
    with pytest.raises(ChangeApprovalError, match="requires DONE"):
        load_active_change_approval(tmp_path / "other")


def test_should_validate_rejection_reason_before_mutation(tmp_path: Path) -> None:
    session = _workspace(tmp_path)
    risk = assess_change_risk((ProjectChange("src/report.py", "modified"),))
    request_active_change_approval(tmp_path, risk)
    before = (session / "change-approval.json").read_text(encoding="utf-8")

    with pytest.raises(ChangeApprovalError, match="must not be empty"):
        reject_active_change(tmp_path, "  ")
    with pytest.raises(ChangeApprovalError, match="too long"):
        reject_active_change(tmp_path, "x" * 501)

    assert (session / "change-approval.json").read_text(encoding="utf-8") == before
