import os
import pty
import select
import subprocess
import sys
import time
from pathlib import Path

from sdd_tdd_agent.workspace_attachments import WorkspaceAttachments


PROMPT_SCRIPT = """\
import sys
from pathlib import Path
from sdd_tdd_agent.interactive_shell import PromptToolkitTerminal
terminal = PromptToolkitTerminal()
terminal.configure(Path(sys.argv[1]))
terminal.prompt("You > ")
"""


def test_should_render_file_menu_after_chinese_text_in_real_pty(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "app.py").write_text("pass\n", encoding="utf-8")
    master, slave = pty.openpty()
    environment = dict(os.environ, NO_COLOR="1", TERM="xterm-256color")
    process = subprocess.Popen(
        (sys.executable, "-c", PROMPT_SCRIPT, str(tmp_path)),
        stdin=slave,
        stdout=slave,
        stderr=slave,
        env=environment,
        close_fds=True,
    )
    os.close(slave)
    output = bytearray()
    try:
        os.write(master, "检查@".encode())
        deadline = time.monotonic() + 1
        while b"src/" not in output and time.monotonic() < deadline:
            readable, _, _ = select.select((master,), (), (), 0.1)
            if readable:
                output.extend(os.read(master, 65_536))
    finally:
        process.terminate()
        process.wait(timeout=2)
        os.close(master)

    assert b"src/" in output
    assert b"directory" in output


def test_should_capture_file_mention_after_chinese_text(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "app.py").write_text("pass\n", encoding="utf-8")

    attachments = WorkspaceAttachments(tmp_path).capture_from_text("请检查@src/app.py")

    assert [attachment.path for attachment in attachments] == ["src/app.py"]
    assert (
        WorkspaceAttachments(tmp_path).capture_from_text("Contact user@example.com")
        == ()
    )
