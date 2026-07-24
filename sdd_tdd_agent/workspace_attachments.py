import hashlib
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import List, Optional, Tuple

from sdd_tdd_agent.git_integration import (
    GIT_TIMEOUT_SECONDS,
    GitCommandRunner,
    GitIntegrationError,
    SystemGitCommandRunner,
)


MAX_ATTACHMENT_BYTES = 1_000_000
MAX_ATTACHMENT_TOTAL_BYTES = 2_000_000
MAX_ATTACHMENTS = 20
MAX_SCANNED_FILES = 5_000
MAX_SCAN_DEPTH = 12
EXCLUDED_DIRECTORIES = {
    ".agent",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}
ATTACHMENT_PATTERN = re.compile(r'(?<!\S)@(?:"([^"\r\n]+)"|([^\s]+))')
GIT_FILES_COMMAND = (
    "git",
    "ls-files",
    "-z",
    "--cached",
    "--others",
    "--exclude-standard",
)


@dataclass(frozen=True)
class AttachmentSnapshot:
    """One bounded UTF-8 project file captured for a Provider request."""

    path: str
    content: str
    sha256: str
    size: int
    device: int
    inode: int
    modified_ns: int


class WorkspaceAttachments:
    """Discover and verify safe project-local attachment files."""

    def __init__(
        self,
        root: Path,
        git_runner: Optional[GitCommandRunner] = None,
    ) -> None:
        self._root = root.resolve()
        self._git_runner = git_runner or SystemGitCommandRunner()

    def paths(self) -> Tuple[str, ...]:
        """List bounded completion paths without ignored dependencies."""
        git_marker = self._root / ".git"
        files = (
            self._git_paths()
            if git_marker.exists() and not git_marker.is_symlink()
            else self._scan()
        )
        directories = {
            f"{parent.as_posix()}/"
            for value in files
            for parent in PurePosixPath(value).parents
            if parent.as_posix() != "."
        }
        return tuple(sorted(directories | set(files)))

    def capture(self, relative_path: str) -> AttachmentSnapshot:
        """Capture one safe file and its concurrency identity."""
        normalized = _relative_path(relative_path)
        path = self._target(normalized)
        try:
            before = path.stat()
            if not stat.S_ISREG(before.st_mode):
                raise ValueError("Attachment must be a regular file")
            if before.st_size > MAX_ATTACHMENT_BYTES:
                raise ValueError("Attachment is too large")
            content = path.read_bytes()
            after = path.stat()
        except ValueError:
            raise
        except OSError as error:
            raise ValueError("Attachment could not be read") from error
        if _identity(before) != _identity(after) or len(content) != after.st_size:
            raise ValueError("Attachment changed while reading")
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("Attachment is not valid UTF-8") from error
        return AttachmentSnapshot(
            normalized.as_posix(),
            text,
            hashlib.sha256(content).hexdigest(),
            after.st_size,
            after.st_dev,
            after.st_ino,
            after.st_mtime_ns,
        )

    def capture_from_text(self, value: str) -> Tuple[AttachmentSnapshot, ...]:
        """Capture each unique @path referenced by one composer submission."""
        references = tuple(
            dict.fromkeys(
                quoted or plain for quoted, plain in ATTACHMENT_PATTERN.findall(value)
            )
        )
        if len(references) > MAX_ATTACHMENTS:
            raise ValueError("Too many attachments")
        snapshots = tuple(self.capture(reference) for reference in references)
        if sum(snapshot.size for snapshot in snapshots) > MAX_ATTACHMENT_TOTAL_BYTES:
            raise ValueError("Attachments exceed the total size limit")
        return snapshots

    def verify(self, snapshot: AttachmentSnapshot) -> None:
        """Reject a captured file that changed before Provider submission."""
        try:
            current = self.capture(snapshot.path)
        except ValueError as error:
            raise ValueError("Attachment changed before sending") from error
        if current != snapshot:
            raise ValueError("Attachment changed before sending")

    def _target(self, relative: PurePosixPath) -> Path:
        current = self._root
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError("Attachment path contains a symbolic link")
        try:
            current.resolve().relative_to(self._root)
        except ValueError as error:
            raise ValueError("Attachment path escapes the project") from error
        return current

    def _git_paths(self) -> Tuple[str, ...]:
        try:
            result = self._git_runner.run(
                GIT_FILES_COMMAND,
                self._root,
                GIT_TIMEOUT_SECONDS,
            )
        except GitIntegrationError as error:
            raise ValueError("Git file discovery failed") from error
        if result.returncode != 0:
            raise ValueError("Git file discovery failed")
        values = result.stdout.split("\0")
        if values and values[-1] == "":
            values.pop()
        if any(not value for value in values) or len(values) > MAX_SCANNED_FILES:
            raise ValueError("Git file discovery returned invalid paths")
        paths: List[str] = []
        for value in values:
            relative = _relative_path(value)
            target = self._target(relative)
            if target.is_file() and not target.is_symlink():
                paths.append(relative.as_posix())
        return tuple(sorted(set(paths)))

    def _scan(self) -> Tuple[str, ...]:
        paths: List[str] = []
        for current, directories, files in os.walk(
            self._root,
            topdown=True,
            followlinks=False,
        ):
            current_path = Path(current)
            depth = len(current_path.relative_to(self._root).parts)
            directories[:] = sorted(
                directory
                for directory in directories
                if directory not in EXCLUDED_DIRECTORIES
                and not (current_path / directory).is_symlink()
                and depth < MAX_SCAN_DEPTH
            )
            for filename in sorted(files):
                path = current_path / filename
                if path.is_symlink() or not path.is_file():
                    continue
                paths.append(path.relative_to(self._root).as_posix())
                if len(paths) > MAX_SCANNED_FILES:
                    raise ValueError("Workspace contains too many files")
        return tuple(paths)


def _identity(metadata: os.stat_result) -> Tuple[int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
    )


def _relative_path(value: str) -> PurePosixPath:
    normalized = value.replace("\\", "/").rstrip("/")
    if (
        not normalized
        or normalized.startswith("/")
        or "\x00" in normalized
        or any(ord(character) < 32 for character in normalized)
        or any(part in {"", ".", ".."} for part in normalized.split("/"))
    ):
        raise ValueError("Attachment path is invalid")
    return PurePosixPath(normalized)
