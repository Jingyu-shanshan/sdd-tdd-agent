from pathlib import Path
from typing import Tuple

from sdd_tdd_agent.git_integration import GitCommandResult
from sdd_tdd_agent.workspace_diff import (
    GitWorkspaceDiff,
    WorkspaceDiffSnapshot,
)


class DiffRunner:
    def __init__(self, diff: str, untracked: str = "") -> None:
        self.diff = diff
        self.untracked = untracked
        self.commands: list[Tuple[str, ...]] = []

    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> GitCommandResult:
        del cwd, timeout_seconds
        self.commands.append(command)
        if command[1] == "diff":
            return GitCommandResult(0, self.diff, "")
        return GitCommandResult(0, self.untracked, "")


def test_should_collect_tracked_and_untracked_unified_diffs(
    tmp_path: Path,
) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "new.py").write_text("print('new')\n", encoding="utf-8")
    tracked = (
        "diff --git a/app.py b/app.py\n"
        "--- a/app.py\n"
        "+++ b/app.py\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
    )
    runner = DiffRunner(tracked, "new.py\0")

    snapshot = GitWorkspaceDiff(tmp_path, runner).snapshot()

    assert len(snapshot.sections) == 2
    assert snapshot.sections[0][0] == "diff --git a/app.py b/app.py"
    assert "-old\n+new" in snapshot.sections[0][1]
    assert snapshot.sections[1][0] == "untracked:new.py"
    assert "--- /dev/null" in snapshot.sections[1][1]
    assert "+print('new')" in snapshot.sections[1][1]


def test_should_return_only_diff_sections_changed_since_snapshot() -> None:
    before = WorkspaceDiffSnapshot(
        (
            ("app.py", "old app diff"),
            ("tests.py", "stable test diff"),
        )
    )
    after = WorkspaceDiffSnapshot(
        (
            ("app.py", "new app diff"),
            ("tests.py", "stable test diff"),
        )
    )

    assert after.changed_since(before) == ("new app diff",)


def test_should_ignore_non_git_workspace(tmp_path: Path) -> None:
    runner = DiffRunner("unexpected")

    assert GitWorkspaceDiff(tmp_path, runner).snapshot().sections == ()
    assert runner.commands == []
