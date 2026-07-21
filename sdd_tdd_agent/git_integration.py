import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Tuple

from sdd_tdd_agent.change_approval import (
    ChangeApproval,
    ChangeApprovalError,
    ProjectChange,
    assess_change_risk,
    load_active_change_approval,
    request_active_change_approval,
)
from sdd_tdd_agent.green_verification import (
    GreenVerificationError,
    validate_production_source_artifact,
)
from sdd_tdd_agent.project_status import load_project_status
from sdd_tdd_agent.red_execution import (
    RedExecutionError,
    validate_current_test_source_artifact,
)
from sdd_tdd_agent.tdd_cycle import load_current_test_case


GIT_TIMEOUT_SECONDS = 30.0
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")


class GitIntegrationError(RuntimeError):
    """Safe public error raised by scoped GREEN-cycle Git integration."""


@dataclass(frozen=True)
class GitCommandResult:
    """Captured Git result without logging process content."""

    returncode: int
    stdout: str
    stderr: str


class GitCommandRunner(Protocol):
    """Typed mockable boundary for shell-free Git commands."""

    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> GitCommandResult:
        """Run one tokenized Git command from an explicit project root."""
        ...


class SystemGitCommandRunner:
    """Production Git runner using an explicit cwd and no command shell."""

    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> GitCommandResult:
        """Run a bounded tokenized Git command without a shell."""
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as error:
            raise GitIntegrationError("Git command timed out") from error
        except OSError as error:
            raise GitIntegrationError("Git command could not be started") from error
        return GitCommandResult(
            completed.returncode,
            completed.stdout,
            completed.stderr,
        )


@dataclass(frozen=True)
class GreenGitPlan:
    """One exact GREEN-cycle commit candidate and approval state."""

    session_id: str
    test_id: str
    paths: Tuple[str, ...]
    change_digest: str
    risk_level: str
    approval_decision: str


@dataclass(frozen=True)
class GreenGitCommit:
    """Verified identity returned after one exact GREEN-cycle commit."""

    session_id: str
    test_id: str
    paths: Tuple[str, ...]
    change_digest: str
    commit_sha: str


@dataclass(frozen=True)
class _GreenContext:
    session_id: str
    test_id: str
    session_path: Path
    state_path: Path
    raw_state: str
    paths: Tuple[str, ...]


def _kind(status: str) -> str:
    if status == "??" or "A" in status:
        return "added"
    if "D" in status:
        return "deleted"
    if "M" in status:
        return "modified"
    raise GitIntegrationError("Git status contains an unsupported change")


def parse_git_status(
    output: str,
    expected_paths: Tuple[str, ...],
) -> Tuple[ProjectChange, ...]:
    """Parse exact NUL-delimited porcelain records for scoped paths."""
    if not output:
        raise GitIntegrationError("Git status is missing expected paths")
    if not output.endswith("\0"):
        raise GitIntegrationError("Git status must be NUL-delimited")
    changes = []
    for record in output[:-1].split("\0"):
        if len(record) < 4 or record[2] != " ":
            raise GitIntegrationError("Git status record is invalid")
        status = record[:2]
        if "R" in status or "C" in status:
            raise GitIntegrationError("Git status contains an unsupported change")
        changes.append(ProjectChange(record[3:], _kind(status)))
    paths = tuple(item.path for item in changes)
    if len(set(paths)) != len(paths):
        raise GitIntegrationError("Git status paths must be unique")
    if set(paths) - set(expected_paths):
        raise GitIntegrationError("Git status is not scoped to expected paths")
    if set(paths) != set(expected_paths):
        raise GitIntegrationError("Git status is missing expected paths")
    return tuple(sorted(changes, key=lambda item: item.path))


def _read_context(root: Path) -> _GreenContext:
    try:
        status = load_project_status(root)
        if status.current_session is None:
            raise GitIntegrationError("Project has no active Session")
        if status.session_state != "IMPLEMENTATION":
            raise GitIntegrationError("Git integration requires active GREEN state")
        session_id = status.current_session
        case = load_current_test_case(root, session_id, "GREEN")
        test = validate_current_test_source_artifact(root, session_id, "GREEN")
        production = validate_production_source_artifact(root, session_id, "GREEN")
        if test.test_id != case.test_id or production.test_id != case.test_id:
            raise GitIntegrationError("GREEN artifacts are stale")
        paths = tuple(sorted((test.file_path, production.file_path)))
        if len(set(paths)) != 2:
            raise GitIntegrationError("GREEN artifact paths must be unique")
        session_path = root / ".agent" / "sessions" / session_id
        state_path = session_path / "state.json"
        raw_state = state_path.read_text(encoding="utf-8")
    except GitIntegrationError:
        raise
    except (
        OSError,
        UnicodeError,
        ValueError,
        RedExecutionError,
        GreenVerificationError,
    ) as error:
        raise GitIntegrationError("Unable to load validated GREEN artifacts") from error
    return _GreenContext(
        session_id,
        case.test_id,
        session_path,
        state_path,
        raw_state,
        paths,
    )


def _same_context(root: Path, before: _GreenContext) -> _GreenContext:
    after = _read_context(root)
    if after != before:
        raise GitIntegrationError("GREEN artifacts changed concurrently")
    return after


def _status_command(paths: Tuple[str, ...]) -> Tuple[str, ...]:
    return (
        "git",
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--",
        *paths,
    )


def _changes(
    root: Path,
    context: _GreenContext,
    runner: GitCommandRunner,
) -> Tuple[ProjectChange, ...]:
    result = runner.run(
        _status_command(context.paths), root.resolve(), GIT_TIMEOUT_SECONDS
    )
    if result.returncode != 0:
        raise GitIntegrationError("Git status failed")
    return parse_git_status(result.stdout, context.paths)


def prepare_active_green_commit(
    root: Path,
    runner: GitCommandRunner,
) -> GreenGitPlan:
    """Prepare an exact GREEN-cycle approval without mutating Git."""
    context = _read_context(root)
    risk = assess_change_risk(_changes(root, context, runner))
    _same_context(root, context)
    try:
        approval = request_active_change_approval(root, risk)
    except ChangeApprovalError as error:
        raise GitIntegrationError(str(error)) from error
    return GreenGitPlan(
        context.session_id,
        context.test_id,
        context.paths,
        risk.change_digest,
        risk.level,
        approval.decision,
    )


def _approved(root: Path) -> ChangeApproval:
    try:
        approval = load_active_change_approval(root)
    except ChangeApprovalError as error:
        raise GitIntegrationError(str(error)) from error
    if approval.decision not in {"approved", "not_required"}:
        raise GitIntegrationError("Git commit requires an approved change")
    return approval


def _run_step(
    runner: GitCommandRunner,
    command: Tuple[str, ...],
    root: Path,
    failure: str,
) -> GitCommandResult:
    result = runner.run(command, root.resolve(), GIT_TIMEOUT_SECONDS)
    if result.returncode != 0:
        raise GitIntegrationError(failure)
    return result


def _cached_paths(output: str, expected: Tuple[str, ...]) -> None:
    if not output.endswith("\0"):
        raise GitIntegrationError("Git staged paths are invalid")
    paths = tuple(item for item in output[:-1].split("\0") if item)
    if len(paths) != len(set(paths)) or set(paths) != set(expected):
        raise GitIntegrationError("Git staged paths do not match GREEN artifacts")


def _verify_digest(
    root: Path,
    context: _GreenContext,
    approval: ChangeApproval,
    runner: GitCommandRunner,
) -> None:
    risk = assess_change_risk(_changes(root, context, runner))
    if risk.change_digest != approval.change_digest:
        raise GitIntegrationError("Git change digest does not match approval")
    _same_context(root, context)


def _archive_approval(context: _GreenContext, digest: str) -> None:
    source = context.session_path / "change-approval.json"
    target = context.session_path / f"change-approval.{digest}.json"
    if target.exists() or target.is_symlink():
        raise GitIntegrationError("Git approval archive already exists")
    try:
        source.replace(target)
    except OSError as error:
        raise GitIntegrationError("Git approval could not be archived") from error


def commit_active_green_cycle(
    root: Path,
    runner: GitCommandRunner,
) -> GreenGitCommit:
    """Commit only approved digest-bound test and production GREEN artifacts."""
    context = _read_context(root)
    approval = _approved(root)
    archive = context.session_path / f"change-approval.{approval.change_digest}.json"
    if archive.exists() or archive.is_symlink():
        raise GitIntegrationError("Git approval archive already exists")
    _verify_digest(root, context, approval, runner)
    _run_step(runner, ("git", "add", "--", *context.paths), root, "Git staging failed")
    cached = _run_step(
        runner,
        ("git", "diff", "--cached", "--name-only", "-z", "--", *context.paths),
        root,
        "Git staged-path verification failed",
    )
    _cached_paths(cached.stdout, context.paths)
    _verify_digest(root, context, approval, runner)
    message = f"feat: {context.session_id} {context.test_id}"
    _run_step(
        runner,
        ("git", "commit", "--only", "-m", message, "--", *context.paths),
        root,
        "Git commit failed",
    )
    head = _run_step(
        runner,
        ("git", "rev-parse", "--verify", "HEAD"),
        root,
        "Git commit identity verification failed",
    ).stdout.strip()
    if COMMIT_PATTERN.fullmatch(head) is None:
        raise GitIntegrationError("Git commit identity is invalid")
    current = _approved(root)
    if current != approval:
        raise GitIntegrationError("Git approval changed concurrently")
    _archive_approval(context, approval.change_digest)
    return GreenGitCommit(
        context.session_id,
        context.test_id,
        context.paths,
        approval.change_digest,
        head,
    )
