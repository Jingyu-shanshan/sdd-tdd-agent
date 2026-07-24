import difflib
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Protocol, Tuple

from sdd_tdd_agent.git_integration import (
    GIT_TIMEOUT_SECONDS,
    GitCommandRunner,
    GitIntegrationError,
    SystemGitCommandRunner,
)
from sdd_tdd_agent.workspace_attachments import WorkspaceAttachments


DIFF_COMMAND = ("git", "diff", "--no-ext-diff", "--no-color", "--")
UNTRACKED_COMMAND = (
    "git",
    "ls-files",
    "--others",
    "--exclude-standard",
    "-z",
)
MAX_DIFF_FILES = 50
MAX_DIFF_CHARACTERS = 200_000


@dataclass(frozen=True)
class WorkspaceDiffSnapshot:
    """Bounded unified-diff sections keyed by one workspace path."""

    sections: Tuple[Tuple[str, str], ...]

    def changed_since(
        self,
        previous: "WorkspaceDiffSnapshot",
    ) -> Tuple[str, ...]:
        """Return current sections whose content changed since a snapshot."""
        before = dict(previous.sections)
        return tuple(
            content for key, content in self.sections if before.get(key) != content
        )


class WorkspaceDiffCollector(Protocol):
    """Mockable read-only boundary for current workspace changes."""

    def snapshot(self) -> WorkspaceDiffSnapshot:
        """Return one bounded current diff snapshot."""
        ...


class GitWorkspaceDiff:
    """Read bounded local Git changes without modifying the repository."""

    def __init__(
        self,
        root: Path,
        runner: Optional[GitCommandRunner] = None,
    ) -> None:
        self._root = root.resolve()
        self._runner = runner or SystemGitCommandRunner()

    def snapshot(self) -> WorkspaceDiffSnapshot:
        """Collect tracked and safe UTF-8 untracked changes."""
        marker = self._root / ".git"
        if not marker.exists() or marker.is_symlink():
            return WorkspaceDiffSnapshot(())
        try:
            tracked = self._runner.run(
                DIFF_COMMAND,
                self._root,
                GIT_TIMEOUT_SECONDS,
            )
            untracked = self._runner.run(
                UNTRACKED_COMMAND,
                self._root,
                GIT_TIMEOUT_SECONDS,
            )
        except GitIntegrationError:
            return WorkspaceDiffSnapshot(())
        if tracked.returncode != 0 or untracked.returncode != 0:
            return WorkspaceDiffSnapshot(())
        sections = _tracked_sections(tracked.stdout)
        sections.extend(_untracked_sections(self._root, untracked.stdout))
        sections.sort(key=lambda item: item[0])
        return WorkspaceDiffSnapshot(tuple(sections[:MAX_DIFF_FILES]))


def _tracked_sections(value: str) -> List[Tuple[str, str]]:
    if not value.startswith("diff --git "):
        return []
    sections = []
    for part in value[len("diff --git ") :].split("\ndiff --git "):
        content = _bounded("diff --git " + part)
        key = content.partition("\n")[0]
        sections.append((key, content))
    return sections


def _untracked_sections(
    root: Path,
    value: str,
) -> List[Tuple[str, str]]:
    paths = value.split("\0")
    if paths and paths[-1] == "":
        paths.pop()
    if len(paths) > MAX_DIFF_FILES:
        return []
    attachments = WorkspaceAttachments(root)
    sections = []
    for path in sorted(set(paths)):
        try:
            snapshot = attachments.capture(path)
        except ValueError:
            continue
        body = "".join(
            difflib.unified_diff(
                (),
                snapshot.content.splitlines(keepends=True),
                fromfile="/dev/null",
                tofile=f"b/{snapshot.path}",
                lineterm="\n",
            )
        )
        content = (
            f"diff --git a/{snapshot.path} b/{snapshot.path}\n"
            "new file mode 100644\n"
            f"{body}"
        )
        sections.append((f"untracked:{snapshot.path}", _bounded(content)))
    return sections


def _bounded(value: str) -> str:
    if len(value) <= MAX_DIFF_CHARACTERS:
        return value
    return value[:MAX_DIFF_CHARACTERS] + "\n... diff truncated ...\n"
