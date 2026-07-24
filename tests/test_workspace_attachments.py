from pathlib import Path
from typing import Tuple

import pytest

from sdd_tdd_agent.git_integration import GitCommandResult
from sdd_tdd_agent.workspace_attachments import WorkspaceAttachments


class GitFilesRunner:
    def __init__(self, output: str) -> None:
        self.output = output
        self.calls: list[Tuple[str, ...]] = []

    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> GitCommandResult:
        self.calls.append(command)
        return GitCommandResult(0, self.output, "")


def test_should_list_git_files_and_attach_verified_utf8_content(
    tmp_path: Path,
) -> None:
    (tmp_path / ".git").mkdir()
    source = tmp_path / "src"
    source.mkdir()
    (source / "app.py").write_text("print('hello')\n", encoding="utf-8")
    runner = GitFilesRunner("src/app.py\0")
    attachments = WorkspaceAttachments(tmp_path, runner)

    assert attachments.paths() == ("src/", "src/app.py")
    snapshot = attachments.capture("src/app.py")
    attachments.verify(snapshot)

    assert snapshot.path == "src/app.py"
    assert snapshot.content == "print('hello')\n"
    assert runner.calls == [
        ("git", "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    ]


def test_should_reject_attachment_changed_before_send(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("before", encoding="utf-8")
    attachments = WorkspaceAttachments(tmp_path)
    snapshot = attachments.capture("notes.txt")
    path.write_text("after", encoding="utf-8")

    with pytest.raises(ValueError, match="changed before sending"):
        attachments.verify(snapshot)


def test_should_capture_quoted_attachment_path_with_spaces(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source files"
    source.mkdir()
    (source / "app.py").write_text("pass\n", encoding="utf-8")

    snapshots = WorkspaceAttachments(tmp_path).capture_from_text(
        'Review @"source files/app.py"'
    )

    assert [snapshot.path for snapshot in snapshots] == ["source files/app.py"]


def test_should_exclude_non_git_dependency_and_agent_directories(
    tmp_path: Path,
) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("pass\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "secret.js").write_text("x", encoding="utf-8")
    (tmp_path / ".agent").mkdir()
    (tmp_path / ".agent" / "secret.txt").write_text("x", encoding="utf-8")

    assert WorkspaceAttachments(tmp_path).paths() == ("src/", "src/app.py")


def test_should_reject_symlink_and_oversized_attachment(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-attachment.txt"
    outside.write_text("private", encoding="utf-8")
    (tmp_path / "linked.txt").symlink_to(outside)
    (tmp_path / "large.txt").write_bytes(b"x" * (1_000_001))
    attachments = WorkspaceAttachments(tmp_path)

    with pytest.raises(ValueError, match="symbolic link"):
        attachments.capture("linked.txt")
    with pytest.raises(ValueError, match="too large"):
        attachments.capture("large.txt")
