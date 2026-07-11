import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sdd_tdd_agent.cli import hello, main


class HelloCommandTest(unittest.TestCase):
    def test_writes_greeting(self) -> None:
        output = io.StringIO()

        hello(output)

        self.assertEqual("Hello, World!\n", output.getvalue())


class ModuleCommandTest(unittest.TestCase):
    def test_hello_command_succeeds(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "sdd_tdd_agent", "hello"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("Hello, World!\n", result.stdout)


class InitCommandTest(unittest.TestCase):
    def test_initializes_selected_project(self) -> None:
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            exit_code = main(["init"], output, root)

            self.assertEqual(0, exit_code)
            self.assertEqual("Initialized .agent workspace.\n", output.getvalue())
            self.assertTrue((root / ".agent" / "project.yml").is_file())


if __name__ == "__main__":
    unittest.main()
