import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple, cast


SCHEMA_VERSION = 1
MAX_FAILURES = 1_000
MAX_SESSIONS_PER_FAILURE = 100
MAX_MEMORY_BYTES = 1_000_000
MAX_OCCURRENCES = 1_000_000_000
SESSION_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
MEMORY_FIELDS = {
    "fingerprint",
    "operation",
    "kind",
    "tool",
    "failure_mode",
    "returncode",
    "occurrences",
    "session_ids",
}


class FailureMemoryError(RuntimeError):
    """Safe public error for persistent content-free failure memory."""


@dataclass(frozen=True)
class FailureMemory:
    """One bounded recurring failure signature without private output."""

    fingerprint: str
    operation: str
    kind: str
    tool: str
    failure_mode: str
    returncode: Optional[int]
    occurrences: int
    session_ids: Tuple[str, ...]


def _identifier(value: str, label: str) -> str:
    pattern = SESSION_PATTERN if label == "Session" else NAME_PATTERN
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise FailureMemoryError(f"Failure memory {label} is invalid")
    return value


def _signature(
    operation: str,
    kind: str,
    tool: str,
    failure_mode: str,
    returncode: Optional[int],
) -> str:
    payload = json.dumps(
        [operation, kind, tool, failure_mode, returncode],
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _validate_signature(
    operation: str,
    kind: str,
    tool: str,
    failure_mode: str,
    returncode: Optional[int],
) -> None:
    _identifier(operation, "operation")
    _identifier(tool, "tool")
    if kind not in {"model", "test"}:
        raise FailureMemoryError("Failure memory kind is invalid")
    if failure_mode not in {"exception", "nonzero_exit"}:
        raise FailureMemoryError("Failure memory mode is invalid")
    if (
        failure_mode == "exception"
        and returncode is not None
        or failure_mode == "nonzero_exit"
        and (
            isinstance(returncode, bool)
            or not isinstance(returncode, int)
            or returncode == 0
        )
    ):
        raise FailureMemoryError("Failure memory return code is invalid")


def _path(root: Path, create: bool) -> Path:
    workspace = root.resolve() / ".agent"
    directory = workspace / "memories"
    if workspace.is_symlink() or directory.is_symlink():
        raise FailureMemoryError("Failure memory path is unsafe")
    try:
        if create:
            directory.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise FailureMemoryError(
            "Failure memory directory could not be prepared"
        ) from error
    result = directory / "failures.json"
    if result.is_symlink():
        raise FailureMemoryError("Failure memory path is unsafe")
    return result


def _decode_memory(value: object) -> FailureMemory:
    if not isinstance(value, dict) or set(value) != MEMORY_FIELDS:
        raise FailureMemoryError("Failure memory record is invalid")
    record: Dict[str, object] = value
    fingerprint = record["fingerprint"]
    operation = record["operation"]
    kind = record["kind"]
    tool = record["tool"]
    failure_mode = record["failure_mode"]
    returncode = record["returncode"]
    occurrences = record["occurrences"]
    session_ids = record["session_ids"]
    if (
        not isinstance(fingerprint, str)
        or SHA256_PATTERN.fullmatch(fingerprint) is None
        or not isinstance(operation, str)
        or not isinstance(kind, str)
        or not isinstance(tool, str)
        or not isinstance(failure_mode, str)
        or (returncode is not None and not isinstance(returncode, int))
        or isinstance(returncode, bool)
        or isinstance(occurrences, bool)
        or not isinstance(occurrences, int)
        or not 1 <= occurrences <= MAX_OCCURRENCES
        or not isinstance(session_ids, list)
        or not 1 <= len(session_ids) <= MAX_SESSIONS_PER_FAILURE
        or any(not isinstance(item, str) for item in session_ids)
        or len(set(session_ids)) != len(session_ids)
    ):
        raise FailureMemoryError("Failure memory record is invalid")
    typed_returncode = cast(Optional[int], returncode)
    _validate_signature(operation, kind, tool, failure_mode, typed_returncode)
    if fingerprint != _signature(
        operation,
        kind,
        tool,
        failure_mode,
        typed_returncode,
    ):
        raise FailureMemoryError("Failure memory fingerprint is invalid")
    sessions = tuple(_identifier(cast(str, item), "Session") for item in session_ids)
    return FailureMemory(
        fingerprint,
        operation,
        kind,
        tool,
        failure_mode,
        typed_returncode,
        occurrences,
        sessions,
    )


def _load(root: Path) -> Tuple[Optional[str], Tuple[FailureMemory, ...]]:
    path = _path(root, create=False)
    if not path.exists():
        return None, ()
    try:
        if path.stat().st_size > MAX_MEMORY_BYTES:
            raise FailureMemoryError("Failure memory file is too large")
        raw = path.read_text(encoding="utf-8")
        value = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise FailureMemoryError("Failure memory file is invalid") from error
    if (
        not isinstance(value, dict)
        or set(value) != {"schema_version", "failures"}
        or value["schema_version"] != SCHEMA_VERSION
        or not isinstance(value["failures"], list)
        or len(value["failures"]) > MAX_FAILURES
    ):
        raise FailureMemoryError("Failure memory file is invalid")
    memories = tuple(_decode_memory(item) for item in value["failures"])
    if tuple(sorted(memory.fingerprint for memory in memories)) != tuple(
        memory.fingerprint for memory in memories
    ) or len({memory.fingerprint for memory in memories}) != len(memories):
        raise FailureMemoryError("Failure memory file is invalid")
    return raw, memories


def load_failure_memories(root: Path) -> Tuple[FailureMemory, ...]:
    """Load and strictly validate bounded project failure memory."""
    return _load(root)[1]


def _payload(memories: Tuple[FailureMemory, ...]) -> str:
    return f"{json.dumps({'schema_version': SCHEMA_VERSION, 'failures': [asdict(memory) for memory in memories]}, indent=2)}\n"


def _updated_memory(
    existing: Optional[FailureMemory],
    session_id: str,
    operation: str,
    kind: str,
    tool: str,
    failure_mode: str,
    returncode: Optional[int],
) -> FailureMemory:
    fingerprint = _signature(operation, kind, tool, failure_mode, returncode)
    sessions = () if existing is None else existing.session_ids
    if session_id not in sessions:
        sessions = (sessions + (session_id,))[-MAX_SESSIONS_PER_FAILURE:]
    occurrences = 1 if existing is None else existing.occurrences + 1
    if occurrences > MAX_OCCURRENCES:
        raise FailureMemoryError("Failure memory occurrence count is too large")
    return FailureMemory(
        fingerprint,
        operation,
        kind,
        tool,
        failure_mode,
        returncode,
        occurrences,
        sessions,
    )


def record_failure(
    root: Path,
    session_id: str,
    operation: str,
    kind: str,
    tool: str,
    failure_mode: str,
    returncode: Optional[int],
) -> FailureMemory:
    """Atomically merge one content-free failure signature into project memory."""
    resolved_session = _identifier(session_id, "Session")
    _validate_signature(operation, kind, tool, failure_mode, returncode)
    raw, memories = _load(root)
    fingerprint = _signature(operation, kind, tool, failure_mode, returncode)
    by_fingerprint = {memory.fingerprint: memory for memory in memories}
    updated = _updated_memory(
        by_fingerprint.get(fingerprint),
        resolved_session,
        operation,
        kind,
        tool,
        failure_mode,
        returncode,
    )
    by_fingerprint[fingerprint] = updated
    if len(by_fingerprint) > MAX_FAILURES:
        raise FailureMemoryError("Failure memory contains too many signatures")
    next_memories = tuple(by_fingerprint[key] for key in sorted(by_fingerprint))
    path = _path(root, create=True)
    temporary = path.with_name(".failures.json.tmp")
    created = False
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            stream.write(_payload(next_memories))
        created = True
        if (path.read_text(encoding="utf-8") if path.exists() else None) != raw:
            raise FailureMemoryError("Failure memory changed concurrently")
        temporary.replace(path)
        created = False
    except FileExistsError as error:
        raise FailureMemoryError(
            "Failure memory update is already in progress"
        ) from error
    except (OSError, UnicodeError) as error:
        raise FailureMemoryError("Failure memory could not be updated") from error
    finally:
        if created and temporary.exists():
            temporary.unlink()
    return updated


def render_failure_memories(memories: Tuple[FailureMemory, ...]) -> str:
    """Render recurring failures without error or project content."""
    lines = [f"Failure memory: {len(memories)} signatures"]
    for memory in sorted(
        memories, key=lambda item: (-item.occurrences, item.fingerprint)
    ):
        exit_text = (
            f" (exit {memory.returncode})" if memory.returncode is not None else ""
        )
        lines.append(
            f"- {memory.operation} | {memory.kind} | {memory.tool} | "
            f"{memory.failure_mode}{exit_text} | {memory.occurrences} occurrences | "
            f"{len(memory.session_ids)} sessions"
        )
    return "\n".join(lines) + "\n"
