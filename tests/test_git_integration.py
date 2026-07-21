from io import StringIO
from pathlib import Path
from typing import Tuple

import pytest

from sdd_tdd_agent.change_approval import approve_active_change, reject_active_change
from sdd_tdd_agent.cli import main
from sdd_tdd_agent.git_integration import (
    GitCommandResult,
    GitIntegrationError,
    SystemGitCommandRunner,
    commit_active_green_cycle,
    parse_git_status,
    prepare_active_green_commit,
)
from tests.cycle_completion_support import create_green_workspace


STATUS = "?? src/export.test.ts\0 M src/export.ts\0"
COMMIT_SHA = "a" * 40


class ScriptedGitRunner:
    def __init__(self, results: Tuple[GitCommandResult, ...]) -> None:
        self.results = list(results)
        self.calls: list[tuple[Tuple[str, ...], Path, float]] = []

    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> GitCommandResult:
        self.calls.append((command, cwd, timeout_seconds))
        if not self.results:
            raise AssertionError("Unexpected Git command")
        return self.results.pop(0)


def _result(
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> GitCommandResult:
    return GitCommandResult(returncode, stdout, stderr)


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


def test_should_parse_strict_scoped_porcelain_status() -> None:
    changes = parse_git_status(
        "?? src/a.test.ts\0M  src/a.ts\0 D docs/old.md\0",
        ("docs/old.md", "src/a.test.ts", "src/a.ts"),
    )

    assert tuple((item.path, item.kind) for item in changes) == (
        ("docs/old.md", "deleted"),
        ("src/a.test.ts", "added"),
        ("src/a.ts", "modified"),
    )


@pytest.mark.parametrize(
    ("output", "paths", "message"),
    [
        ("", ("src/a.py",), "missing"),
        ("R  src/a.py\0src/b.py\0", ("src/a.py",), "unsupported"),
        ("XY src/a.py\0", ("src/a.py",), "unsupported"),
        ("?? src/a.py", ("src/a.py",), "NUL"),
        ("?? src/a.py\0?? src/a.py\0", ("src/a.py",), "unique"),
        ("?? src/b.py\0", ("src/a.py",), "scoped"),
    ],
)
def test_should_reject_invalid_git_status(
    output: str,
    paths: Tuple[str, ...],
    message: str,
) -> None:
    with pytest.raises(GitIntegrationError, match=message):
        parse_git_status(output, paths)


def test_should_prepare_green_cycle_without_mutating_git(tmp_path: Path) -> None:
    create_green_workspace(tmp_path)
    runner = ScriptedGitRunner((_result(stdout=STATUS),))

    plan = prepare_active_green_commit(tmp_path, runner)

    assert plan.session_id == "feature-1"
    assert plan.test_id == "TC1"
    assert plan.paths == ("src/export.test.ts", "src/export.ts")
    assert plan.risk_level == "medium"
    assert plan.approval_decision == "pending"
    assert [call[0] for call in runner.calls] == [_status_command()]


def test_should_commit_only_exact_approved_green_paths(tmp_path: Path) -> None:
    session = create_green_workspace(tmp_path)
    prepare_active_green_commit(
        tmp_path,
        ScriptedGitRunner((_result(stdout=STATUS),)),
    )
    approve_active_change(tmp_path)
    runner = ScriptedGitRunner(
        (
            _result(stdout=STATUS),
            _result(),
            _result(stdout="src/export.test.ts\0src/export.ts\0"),
            _result(stdout=STATUS),
            _result(stdout="SECRET PROCESS OUTPUT"),
            _result(stdout=f"{COMMIT_SHA}\n"),
        )
    )

    committed = commit_active_green_cycle(tmp_path, runner)

    assert committed.session_id == "feature-1"
    assert committed.test_id == "TC1"
    assert committed.commit_sha == COMMIT_SHA
    commands = [call[0] for call in runner.calls]
    assert commands == [
        _status_command(),
        ("git", "add", "--", "src/export.test.ts", "src/export.ts"),
        (
            "git",
            "diff",
            "--cached",
            "--name-only",
            "-z",
            "--",
            "src/export.test.ts",
            "src/export.ts",
        ),
        _status_command(),
        (
            "git",
            "commit",
            "--only",
            "-m",
            "feat: feature-1 TC1",
            "--",
            "src/export.test.ts",
            "src/export.ts",
        ),
        ("git", "rev-parse", "--verify", "HEAD"),
    ]
    assert not (session / "change-approval.json").exists()
    assert (session / f"change-approval.{committed.change_digest}.json").is_file()


@pytest.mark.parametrize("decision", ["pending", "rejected"])
def test_should_block_unapproved_commit_before_git_mutation(
    tmp_path: Path,
    decision: str,
) -> None:
    create_green_workspace(tmp_path)
    prepare_active_green_commit(
        tmp_path,
        ScriptedGitRunner((_result(stdout=STATUS),)),
    )
    if decision == "rejected":
        reject_active_change(tmp_path, "Unsafe.")
    runner = ScriptedGitRunner(())

    with pytest.raises(GitIntegrationError, match="approved"):
        commit_active_green_cycle(tmp_path, runner)

    assert runner.calls == []


def test_should_reject_changed_status_before_staging(tmp_path: Path) -> None:
    create_green_workspace(tmp_path)
    prepare_active_green_commit(
        tmp_path,
        ScriptedGitRunner((_result(stdout=STATUS),)),
    )
    approve_active_change(tmp_path)
    runner = ScriptedGitRunner(
        (_result(stdout=" M src/export.test.ts\0 M src/export.ts\0"),)
    )

    with pytest.raises(GitIntegrationError, match="digest"):
        commit_active_green_cycle(tmp_path, runner)

    assert [call[0] for call in runner.calls] == [_status_command()]


def test_should_reject_nonzero_or_incomplete_git_steps(tmp_path: Path) -> None:
    create_green_workspace(tmp_path)
    with pytest.raises(GitIntegrationError, match="status failed"):
        prepare_active_green_commit(
            tmp_path,
            ScriptedGitRunner((_result(128, stderr="SECRET"),)),
        )

    prepare_active_green_commit(
        tmp_path,
        ScriptedGitRunner((_result(stdout=STATUS),)),
    )
    approve_active_change(tmp_path)
    with pytest.raises(GitIntegrationError, match="staging failed"):
        commit_active_green_cycle(
            tmp_path,
            ScriptedGitRunner(
                (
                    _result(stdout=STATUS),
                    _result(1, stderr="SECRET"),
                )
            ),
        )


def test_should_preserve_approval_when_commit_fails(tmp_path: Path) -> None:
    session = create_green_workspace(tmp_path)
    prepare_active_green_commit(
        tmp_path,
        ScriptedGitRunner((_result(stdout=STATUS),)),
    )
    approve_active_change(tmp_path)
    runner = ScriptedGitRunner(
        (
            _result(stdout=STATUS),
            _result(),
            _result(stdout="src/export.test.ts\0src/export.ts\0"),
            _result(stdout=STATUS),
            _result(1, stderr="SECRET"),
        )
    )

    with pytest.raises(GitIntegrationError, match="commit failed"):
        commit_active_green_cycle(tmp_path, runner)

    assert (session / "change-approval.json").is_file()


def test_should_reject_incomplete_staged_paths(tmp_path: Path) -> None:
    create_green_workspace(tmp_path)
    prepare_active_green_commit(
        tmp_path,
        ScriptedGitRunner((_result(stdout=STATUS),)),
    )
    approve_active_change(tmp_path)
    runner = ScriptedGitRunner(
        (
            _result(stdout=STATUS),
            _result(),
            _result(stdout="src/export.ts\0"),
        )
    )

    with pytest.raises(GitIntegrationError, match="do not match"):
        commit_active_green_cycle(tmp_path, runner)


def test_should_reject_non_nul_staged_path_output(tmp_path: Path) -> None:
    create_green_workspace(tmp_path)
    prepare_active_green_commit(
        tmp_path,
        ScriptedGitRunner((_result(stdout=STATUS),)),
    )
    approve_active_change(tmp_path)
    runner = ScriptedGitRunner(
        (
            _result(stdout=STATUS),
            _result(),
            _result(stdout="src/export.test.ts"),
        )
    )

    with pytest.raises(GitIntegrationError, match="staged paths are invalid"):
        commit_active_green_cycle(tmp_path, runner)


def test_should_reject_invalid_commit_identity_and_preserve_approval(
    tmp_path: Path,
) -> None:
    session = create_green_workspace(tmp_path)
    prepare_active_green_commit(
        tmp_path,
        ScriptedGitRunner((_result(stdout=STATUS),)),
    )
    approve_active_change(tmp_path)
    runner = ScriptedGitRunner(
        (
            _result(stdout=STATUS),
            _result(),
            _result(stdout="src/export.test.ts\0src/export.ts\0"),
            _result(stdout=STATUS),
            _result(),
            _result(stdout="not-a-commit\n"),
        )
    )

    with pytest.raises(GitIntegrationError, match="identity is invalid"):
        commit_active_green_cycle(tmp_path, runner)

    assert (session / "change-approval.json").is_file()


def test_should_reject_approval_archive_collision_before_git_mutation(
    tmp_path: Path,
) -> None:
    session = create_green_workspace(tmp_path)
    plan = prepare_active_green_commit(
        tmp_path,
        ScriptedGitRunner((_result(stdout=STATUS),)),
    )
    approve_active_change(tmp_path)
    (session / f"change-approval.{plan.change_digest}.json").write_text(
        "owner",
        encoding="utf-8",
    )
    runner = ScriptedGitRunner(())

    with pytest.raises(GitIntegrationError, match="archive already exists"):
        commit_active_green_cycle(tmp_path, runner)

    assert runner.calls == []


def test_should_require_active_green_state(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "project.yml").write_text("name: reports\n", encoding="utf-8")

    with pytest.raises(GitIntegrationError, match="no active Session"):
        prepare_active_green_commit(tmp_path, ScriptedGitRunner(()))

    session = create_green_workspace(tmp_path / "other")
    state_path = session / "state.json"
    state = state_path.read_text(encoding="utf-8").replace(
        '"phase": "GREEN"',
        '"phase": "RED"',
    )
    state_path.write_text(state, encoding="utf-8")
    with pytest.raises(GitIntegrationError, match="validated GREEN"):
        prepare_active_green_commit(tmp_path / "other", ScriptedGitRunner(()))


def test_should_run_git_prepare_and_commit_through_cli(tmp_path: Path) -> None:
    create_green_workspace(tmp_path)
    output = StringIO()
    prepare_runner = ScriptedGitRunner((_result(stdout=STATUS),))

    assert (
        main(
            ["git", "prepare"],
            root=tmp_path,
            out=output,
            git_runner=prepare_runner,
        )
        == 0
    )
    assert output.getvalue().startswith("Git commit approval pending: feature-1 (TC1; ")


def test_should_run_system_git_runner_without_shell(tmp_path: Path) -> None:
    result = SystemGitCommandRunner().run(
        ("git", "--version"),
        tmp_path,
        5.0,
    )

    assert result.returncode == 0
    assert result.stdout.startswith("git version ")


def test_should_commit_exact_paths_in_a_real_repository(tmp_path: Path) -> None:
    create_green_workspace(tmp_path)
    runner = SystemGitCommandRunner()
    setup_commands = (
        ("git", "init", "-q"),
        ("git", "config", "user.name", "Test Agent"),
        ("git", "config", "user.email", "agent@example.invalid"),
    )
    for command in setup_commands:
        assert runner.run(command, tmp_path, 5.0).returncode == 0
    (tmp_path / "unrelated.txt").write_text("preserve me\n", encoding="utf-8")
    assert (
        runner.run(("git", "add", "--", "unrelated.txt"), tmp_path, 5.0).returncode == 0
    )

    plan = prepare_active_green_commit(tmp_path, runner)
    approve_active_change(tmp_path)
    committed = commit_active_green_cycle(tmp_path, runner)

    assert committed.change_digest == plan.change_digest
    committed_paths = runner.run(
        ("git", "show", "--pretty=format:", "--name-only", "HEAD"),
        tmp_path,
        5.0,
    )
    assert committed_paths.returncode == 0
    assert set(committed_paths.stdout.split()) == {
        "src/export.test.ts",
        "src/export.ts",
    }
    staged = runner.run(
        ("git", "diff", "--cached", "--name-only"),
        tmp_path,
        5.0,
    )
    assert staged.stdout.strip() == "unrelated.txt"
