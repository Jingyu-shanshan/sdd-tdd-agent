import os
import selectors
import signal
import subprocess
import time
from typing import Callable, Protocol, Tuple

from sdd_tdd_agent.model_adapter import (
    ProcessResult,
    RequirementAnalyzerError,
)


MAX_STREAM_STDOUT_BYTES = 10_000_000
MAX_STREAM_STDERR_BYTES = 1_000_000


class StreamingProcessRunner(Protocol):
    """Mockable boundary for one line-streaming shell-free process."""

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
        on_stdout_line: Callable[[str], None],
    ) -> ProcessResult:
        """Run and report each complete UTF-8 stdout line."""
        ...


class SystemStreamingProcessRunner:
    """Stream stdout from a bounded subprocess on macOS and Linux."""

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
        on_stdout_line: Callable[[str], None],
    ) -> ProcessResult:
        """Execute one tokenized command and capture bounded output."""
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                start_new_session=True,
            )
        except OSError as error:
            raise RequirementAnalyzerError(
                "Provider streaming command could not be started"
            ) from error
        try:
            if process.stdin is not None:
                try:
                    process.stdin.write(stdin.encode("utf-8"))
                    process.stdin.close()
                except BrokenPipeError:
                    pass
            return self._collect(
                process,
                timeout_seconds,
                on_stdout_line,
            )
        except KeyboardInterrupt:
            _terminate(process)
            raise
        except OSError as error:
            _terminate(process)
            raise RequirementAnalyzerError(
                "Provider streaming command failed"
            ) from error
        except BaseException:
            _terminate(process)
            raise

    def _collect(
        self,
        process: subprocess.Popen[bytes],
        timeout_seconds: float,
        on_stdout_line: Callable[[str], None],
    ) -> ProcessResult:
        if process.stdout is None or process.stderr is None:
            raise RequirementAnalyzerError("Provider streaming pipes are unavailable")
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        selector.register(process.stderr, selectors.EVENT_READ, "stderr")
        stdout = bytearray()
        stderr = bytearray()
        pending = bytearray()
        deadline = time.monotonic() + timeout_seconds
        try:
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    _terminate(process)
                    raise RequirementAnalyzerError(
                        "Provider streaming command timed out"
                    )
                for key, _ in selector.select(min(remaining, 0.1)):
                    chunk = os.read(key.fd, 65_536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    if key.data == "stderr":
                        stderr.extend(chunk)
                        _check_size(stderr, MAX_STREAM_STDERR_BYTES)
                        continue
                    stdout.extend(chunk)
                    pending.extend(chunk)
                    _check_size(stdout, MAX_STREAM_STDOUT_BYTES)
                    _emit_lines(pending, on_stdout_line)
            if pending:
                _emit_line(bytes(pending), on_stdout_line)
            try:
                returncode = process.wait(max(0.0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired as error:
                _terminate(process)
                raise RequirementAnalyzerError(
                    "Provider streaming command timed out"
                ) from error
        finally:
            selector.close()
        try:
            return ProcessResult(
                returncode,
                stdout.decode("utf-8"),
                stderr.decode("utf-8"),
            )
        except UnicodeDecodeError as error:
            raise RequirementAnalyzerError(
                "Provider stream is not valid UTF-8"
            ) from error


def _check_size(content: bytearray, limit: int) -> None:
    if len(content) > limit:
        raise RequirementAnalyzerError("Provider stream exceeds output limit")


def _emit_lines(
    pending: bytearray,
    on_stdout_line: Callable[[str], None],
) -> None:
    while True:
        newline = pending.find(b"\n")
        if newline < 0:
            return
        line = bytes(pending[:newline])
        del pending[: newline + 1]
        _emit_line(line, on_stdout_line)


def _emit_line(line: bytes, on_stdout_line: Callable[[str], None]) -> None:
    if line.endswith(b"\r"):
        line = line[:-1]
    try:
        on_stdout_line(line.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise RequirementAnalyzerError("Provider stream is not valid UTF-8") from error


def _terminate(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=0.5)
    except (OSError, subprocess.TimeoutExpired):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            process.kill()
        process.wait()
