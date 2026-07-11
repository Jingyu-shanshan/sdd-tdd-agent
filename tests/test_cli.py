import io
import subprocess
import sys
import unittest

from sdd_tdd_agent.cli import hello


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


if __name__ == "__main__":
    unittest.main()
