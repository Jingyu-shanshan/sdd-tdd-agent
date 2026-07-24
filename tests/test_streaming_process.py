import sys
from typing import List

import pytest

from sdd_tdd_agent.model_adapter import RequirementAnalyzerError
from sdd_tdd_agent.streaming_process import SystemStreamingProcessRunner


def test_should_stream_complete_utf8_lines_and_capture_result() -> None:
    lines: List[str] = []
    result = SystemStreamingProcessRunner().run(
        (
            sys.executable,
            "-c",
            "import sys; print('one'); print('two'); print('warning', file=sys.stderr)",
        ),
        "",
        5,
        lines.append,
    )

    assert result.returncode == 0
    assert lines == ["one", "two"]
    assert result.stdout == "one\ntwo\n"
    assert result.stderr == "warning\n"


def test_should_report_streaming_process_start_failure() -> None:
    with pytest.raises(RequirementAnalyzerError, match="could not be started"):
        SystemStreamingProcessRunner().run(
            ("/missing/wssagent-provider",),
            "",
            5,
            lambda line: None,
        )


def test_should_buffer_chunked_jsonl_until_a_complete_line() -> None:
    lines: List[str] = []

    result = SystemStreamingProcessRunner().run(
        (
            sys.executable,
            "-c",
            "import sys,time; sys.stdout.write('{\"type\":'); "
            "sys.stdout.flush(); time.sleep(0.01); "
            "sys.stdout.write('\"result\"}\\n'); sys.stdout.flush()",
        ),
        "",
        5,
        lines.append,
    )

    assert result.returncode == 0
    assert lines == ['{"type":"result"}']


def test_should_stop_a_timed_out_streaming_process() -> None:
    with pytest.raises(RequirementAnalyzerError, match="timed out"):
        SystemStreamingProcessRunner().run(
            (sys.executable, "-c", "import time; time.sleep(5)"),
            "",
            0.01,
            lambda line: None,
        )


def test_should_stop_a_streaming_process_when_cancelled() -> None:
    def cancel(line: str) -> None:
        del line
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        SystemStreamingProcessRunner().run(
            (
                sys.executable,
                "-c",
                "import time; print('started', flush=True); time.sleep(5)",
            ),
            "",
            5,
            cancel,
        )
