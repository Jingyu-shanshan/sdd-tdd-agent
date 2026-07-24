import json
import stat
from pathlib import Path

from sdd_tdd_agent.chat_session import ChatSessionStore


def test_should_create_append_rename_and_resume_private_chat_session(
    tmp_path: Path,
) -> None:
    store = ChatSessionStore(tmp_path, id_factory=lambda: "chat-1")

    created = store.create()
    store.append_message(created.session_id, "user", "Build export")
    store.append_message(created.session_id, "assistant", "Ready.")
    renamed = store.rename(created.session_id, "export-flow")
    loaded = store.load("export-flow")

    assert created.session_id == "chat-1"
    assert renamed.name == "export-flow"
    assert loaded.session_id == "chat-1"
    assert [(message.role, message.content) for message in loaded.messages] == [
        ("user", "Build export"),
        ("assistant", "Ready."),
    ]
    assert store.latest().session_id == "chat-1"
    assert stat.S_IMODE(loaded.path.stat().st_mode) == 0o600
    records = [
        json.loads(line)
        for line in loaded.path.read_text(encoding="utf-8").splitlines()
    ]
    assert records[0]["schema_version"] == 1


def test_should_reject_unknown_or_corrupt_chat_session(tmp_path: Path) -> None:
    store = ChatSessionStore(tmp_path, id_factory=lambda: "chat-1")
    session = store.create()
    session.path.write_text("{\n", encoding="utf-8")

    try:
        store.load(session.session_id)
    except ValueError as error:
        assert str(error) == "Chat session is invalid"
    else:
        raise AssertionError("Corrupt session must fail")
