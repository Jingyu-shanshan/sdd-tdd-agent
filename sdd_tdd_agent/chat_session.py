import json
import os
import re
import stat
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from sdd_tdd_agent.red_execution import sanitize_test_evidence


SCHEMA_VERSION = 1
MAX_SESSION_BYTES = 10 * 1024 * 1024
SESSION_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
ROLES = {"user", "assistant", "event"}


@dataclass(frozen=True)
class ChatMessage:
    """One sanitized message persisted in a local chat session."""

    role: str
    content: str


@dataclass(frozen=True)
class ChatSession:
    """One validated local chat session."""

    session_id: str
    name: str
    path: Path
    messages: Tuple[ChatMessage, ...]


def _default_session_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}-{uuid.uuid4().hex[:8]}"


class ChatSessionStore:
    """Store private, redacted chat history below one project workspace."""

    def __init__(
        self,
        root: Path,
        id_factory: Callable[[], str] = _default_session_id,
    ) -> None:
        self._root = root.resolve()
        self._directory = self._root / ".agent" / "logs" / "chat"
        self._id_factory = id_factory

    def create(self, name: Optional[str] = None) -> ChatSession:
        """Create a new versioned JSONL session with private permissions."""
        session_id = self._id_factory()
        _validate_session_id(session_id)
        session_name = session_id if name is None else _validate_name(name)
        self._directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self._directory, 0o700)
        path = self._directory / f"{session_id}.jsonl"
        record = {
            "schema_version": SCHEMA_VERSION,
            "type": "session",
            "session_id": session_id,
            "name": session_name,
        }
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        descriptor = os.open(path, flags, 0o600)
        try:
            _write_bytes(descriptor, _encode_record(record))
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return ChatSession(session_id, session_name, path, ())

    def append_message(self, session_id: str, role: str, content: str) -> None:
        """Append one sanitized public message without rewriting history."""
        if role not in ROLES:
            raise ValueError("Chat message role is invalid")
        session = self.load(session_id)
        sanitized = sanitize_test_evidence(self._root, content)
        self._append(
            session.path,
            {
                "schema_version": SCHEMA_VERSION,
                "type": "message",
                "role": role,
                "content": sanitized,
            },
        )

    def rename(self, session_ref: str, name: str) -> ChatSession:
        """Assign a validated display name to an existing session."""
        session = self.load(session_ref)
        validated = _validate_name(name)
        self._append(
            session.path,
            {
                "schema_version": SCHEMA_VERSION,
                "type": "rename",
                "name": validated,
            },
        )
        return self.load(session.session_id)

    def load(self, session_ref: str) -> ChatSession:
        """Load one session by identifier or current display name."""
        if not session_ref or len(session_ref) > 128:
            raise ValueError("Chat session reference is invalid")
        direct = (
            self._directory / f"{session_ref}.jsonl"
            if SESSION_ID_PATTERN.fullmatch(session_ref)
            else None
        )
        if direct is not None and direct.is_file() and not direct.is_symlink():
            return self._load_path(direct)
        matches = [session for session in self.list() if session.name == session_ref]
        if len(matches) != 1:
            raise ValueError("Chat session was not found")
        return matches[0]

    def latest(self) -> ChatSession:
        """Load the most recently updated chat session."""
        paths = self._session_paths()
        if not paths:
            raise ValueError("No chat session is available")
        return self._load_path(max(paths, key=lambda path: path.stat().st_mtime_ns))

    def list(self) -> Tuple[ChatSession, ...]:
        """List validated sessions from newest to oldest."""
        paths = sorted(
            self._session_paths(),
            key=lambda path: path.stat().st_mtime_ns,
            reverse=True,
        )
        return tuple(self._load_path(path) for path in paths)

    def _session_paths(self) -> List[Path]:
        if not self._directory.is_dir() or self._directory.is_symlink():
            return []
        return [
            path
            for path in self._directory.iterdir()
            if path.is_file()
            and not path.is_symlink()
            and path.suffix == ".jsonl"
            and SESSION_ID_PATTERN.fullmatch(path.stem)
        ]

    def _load_path(self, path: Path) -> ChatSession:
        try:
            if path.is_symlink() or path.stat().st_size > MAX_SESSION_BYTES:
                raise ValueError("Chat session is invalid")
            lines = path.read_text(encoding="utf-8").splitlines()
            records = [_decode_record(line) for line in lines]
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ValueError("Chat session is invalid") from error
        try:
            return _session_from_records(path, records)
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Chat session is invalid") from error

    def _append(self, path: Path, record: Dict[str, object]) -> None:
        if path.is_symlink():
            raise ValueError("Chat session is invalid")
        content = _encode_record(record)
        flags = os.O_WRONLY | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_size + len(content) > MAX_SESSION_BYTES
            ):
                raise ValueError("Chat session is invalid")
            _write_bytes(descriptor, content)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _write_bytes(descriptor: int, content: bytes) -> None:
    if os.write(descriptor, content) != len(content):
        raise OSError("Chat session write was incomplete")


def _encode_record(record: Dict[str, object]) -> bytes:
    return (
        json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _decode_record(line: str) -> Dict[str, object]:
    value = json.loads(line)
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Chat session record is invalid")
    return value


def _session_from_records(
    path: Path,
    records: List[Dict[str, object]],
) -> ChatSession:
    if not records:
        raise ValueError("Chat session is empty")
    header = records[0]
    session_id = header["session_id"]
    name = header["name"]
    if (
        header.get("type") != "session"
        or not isinstance(session_id, str)
        or not isinstance(name, str)
        or path.stem != session_id
    ):
        raise ValueError("Chat session header is invalid")
    _validate_session_id(session_id)
    current_name = _validate_name(name)
    messages: List[ChatMessage] = []
    for record in records[1:]:
        record_type = record.get("type")
        if record_type == "rename":
            current_name = _validate_name(record["name"])
            continue
        if record_type != "message":
            raise ValueError("Chat session record type is invalid")
        role = record.get("role")
        content = record.get("content")
        if role not in ROLES or not isinstance(content, str):
            raise ValueError("Chat session message is invalid")
        messages.append(ChatMessage(str(role), content))
    return ChatSession(session_id, current_name, path, tuple(messages))


def _validate_session_id(session_id: str) -> None:
    if SESSION_ID_PATTERN.fullmatch(session_id) is None:
        raise ValueError("Chat session identifier is invalid")


def _validate_name(name: object) -> str:
    if (
        not isinstance(name, str)
        or not name.strip()
        or len(name) > 128
        or any(ord(character) < 32 for character in name)
    ):
        raise ValueError("Chat session name is invalid")
    return name.strip()
