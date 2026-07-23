import json
from io import StringIO
from pathlib import Path
from typing import Callable, Optional, Tuple

import pytest

from sdd_tdd_agent.change_approval import approve_active_change
from sdd_tdd_agent.cli import main
from sdd_tdd_agent.git_integration import (
    GitCommandResult,
    GitIntegrationError,
    SystemGitCommandRunner,
    commit_active_green_cycle,
    prepare_active_green_commit,
    rollback_active_green_cycle,
)
from tests.cycle_completion_support import create_green_workspace


HEAD = "a" * 40
PARENT = "b" * 40
PATHS = "src/export.test.ts\0src/export.ts\0"
METADATA = f"{HEAD}\0{PARENT}\0feat: feature-1 TC1\n"


class ScriptedGitRunner:
    def __init__(
        self,
        results: Tuple[GitCommandResult, ...],
        callback: Optional[Callable[[Tuple[str, ...]], None]] = None,
    ) -> None:
        self.results = list(results)
        self.calls: list[Tuple[str, ...]] = []
        self.callback = callback

    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> GitCommandResult:
        self.calls.append(command)
        if self.callback is not None:
            self.callback(command)
        if not self.results:
            raise AssertionError("Unexpected Git command")
        return self.results.pop(0)


def _result(returncode: int = 0, stdout: str = "") -> GitCommandResult:
    return GitCommandResult(returncode, stdout, "SECRET")


def _status_command() -> Tuple[str, ...]:
    return (
        "git",
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--",
        "src/export.test.ts",
        "src/export.ts",
    )


def _show_command() -> Tuple[str, ...]:
    return ("git", "show", "-s", "--format=%H%x00%P%x00%s", "HEAD")


def _paths_command() -> Tuple[str, ...]:
    return (
        "git",
        "diff-tree",
        "--no-commit-id",
        "--name-only",
        "-z",
        "-r",
        "HEAD",
    )


def _restore_command(source: str) -> Tuple[str, ...]:
    return (
        "git",
        "restore",
        f"--source={source}",
        "--worktree",
        "--",
        "src/export.test.ts",
        "src/export.ts",
    )


def _initialize_repository(root: Path, runner: SystemGitCommandRunner) -> None:
    for command in (
        ("git", "init", "-q"),
        ("git", "config", "user.name", "Test Agent"),
        ("git", "config", "user.email", "agent@example.invalid"),
        ("git", "commit", "--allow-empty", "-q", "-m", "base"),
    ):
        assert runner.run(command, root, 5.0).returncode == 0


def test_should_rollback_current_green_commit_through_cli(tmp_path: Path) -> None:
    runner = SystemGitCommandRunner()
    _initialize_repository(tmp_path, runner)
    session = create_green_workspace(tmp_path)
    prepare_active_green_commit(tmp_path, runner)
    approve_active_change(tmp_path)
    committed = commit_active_green_cycle(tmp_path, runner)
    unrelated = tmp_path / "unrelated.txt"
    unrelated.write_text("preserve\n", encoding="utf-8")
    assert (
        runner.run(("git", "add", "--", "unrelated.txt"), tmp_path, 5.0).returncode == 0
    )
    output = StringIO()

    assert main(["rollback"], root=tmp_path, out=output, git_runner=runner) == 0

    assert (
        output.getvalue() == "Rollback ready for retry: feature-1 (TC1; WRITE_TEST)\n"
    )
    assert not (tmp_path / "src" / "export.test.ts").exists()
    assert not (tmp_path / "src" / "export.ts").exists()
    assert (
        runner.run(("git", "rev-parse", "HEAD"), tmp_path, 5.0).stdout.strip()
        == committed.commit_sha
    )
    assert (
        runner.run(
            ("git", "diff", "--cached", "--name-only"), tmp_path, 5.0
        ).stdout.strip()
        == "unrelated.txt"
    )
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["tdd_cycle"] == {
        "current_test": "TC1",
        "phase": "WRITE_TEST",
        "completed_tests": [],
    }
    for field in (
        "test_source",
        "red_evidence",
        "production_source",
        "green_evidence",
        "verification_failure",
    ):
        assert field not in state


def test_should_reject_dirty_target_paths_without_restoring(tmp_path: Path) -> None:
    create_green_workspace(tmp_path)
    runner = ScriptedGitRunner((_result(stdout=" M src/export.ts\0"),))

    with pytest.raises(GitIntegrationError, match="target paths must be clean"):
        rollback_active_green_cycle(tmp_path, runner)

    assert runner.calls == [_status_command()]


@pytest.mark.parametrize(
    ("metadata", "message"),
    [
        (f"{HEAD}\0{PARENT}\0fix: unrelated\n", "does not match"),
        (f"{HEAD}\0{PARENT} {'c' * 40}\0feat: feature-1 TC1\n", "single parent"),
        ("invalid", "metadata is invalid"),
    ],
)
def test_should_reject_untrusted_head_metadata(
    tmp_path: Path,
    metadata: str,
    message: str,
) -> None:
    create_green_workspace(tmp_path)
    runner = ScriptedGitRunner((_result(), _result(stdout=metadata)))

    with pytest.raises(GitIntegrationError, match=message):
        rollback_active_green_cycle(tmp_path, runner)

    assert runner.calls == [_status_command(), _show_command()]


def test_should_reject_mismatched_head_paths(tmp_path: Path) -> None:
    create_green_workspace(tmp_path)
    runner = ScriptedGitRunner(
        (_result(), _result(stdout=METADATA), _result(stdout="src/other.ts\0"))
    )

    with pytest.raises(GitIntegrationError, match="paths do not match"):
        rollback_active_green_cycle(tmp_path, runner)

    assert runner.calls == [_status_command(), _show_command(), _paths_command()]


def test_should_preserve_green_state_when_restore_fails(tmp_path: Path) -> None:
    session = create_green_workspace(tmp_path)
    original = (session / "state.json").read_text(encoding="utf-8")
    runner = ScriptedGitRunner(
        (
            _result(),
            _result(stdout=METADATA),
            _result(stdout=PATHS),
            _result(returncode=1),
        )
    )

    with pytest.raises(GitIntegrationError, match="restore failed"):
        rollback_active_green_cycle(tmp_path, runner)

    assert (session / "state.json").read_text(encoding="utf-8") == original
    assert runner.calls[-1] == _restore_command(PARENT)


def test_should_restore_head_files_after_concurrent_state_change(
    tmp_path: Path,
) -> None:
    session = create_green_workspace(tmp_path)
    state_path = session / "state.json"

    def change_state(command: Tuple[str, ...]) -> None:
        if command == _restore_command(PARENT):
            state_path.write_text('{"owner": "changed"}\n', encoding="utf-8")

    runner = ScriptedGitRunner(
        (
            _result(),
            _result(stdout=METADATA),
            _result(stdout=PATHS),
            _result(),
            _result(),
        ),
        callback=change_state,
    )

    with pytest.raises(GitIntegrationError, match="changed concurrently"):
        rollback_active_green_cycle(tmp_path, runner)

    assert state_path.read_text(encoding="utf-8") == '{"owner": "changed"}\n'
    assert runner.calls[-1] == _restore_command(HEAD)


def test_should_report_safe_cli_error(tmp_path: Path) -> None:
    create_green_workspace(tmp_path)
    output = StringIO()
    errors = StringIO()

    assert (
        main(
            ["rollback"],
            root=tmp_path,
            out=output,
            err=errors,
            git_runner=ScriptedGitRunner((_result(returncode=1),)),
        )
        == 2
    )
    assert output.getvalue() == ""
    assert errors.getvalue() == "Error: Git rollback status failed\n"
    assert "SECRET" not in errors.getvalue()
