import tempfile
import unittest
from pathlib import Path

from sdd_tdd_agent.project_detection import detect_project


class MavenDetectionTest(unittest.TestCase):
    def test_detects_root_pom(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pom.xml").touch()

            profile = detect_project(root)

            self.assertIsNotNone(profile)
            self.assertEqual("java", profile.target_language)
            self.assertEqual("maven", profile.build_tool)


class GradleDetectionTest(unittest.TestCase):
    def test_detects_supported_root_build_files(self) -> None:
        for marker in ("build.gradle", "build.gradle.kts"):
            with self.subTest(marker=marker):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    (root / marker).touch()

                    profile = detect_project(root)

                    self.assertIsNotNone(profile)
                    self.assertEqual("java", profile.target_language)
                    self.assertEqual("gradle", profile.build_tool)


class UnknownProjectDetectionTest(unittest.TestCase):
    def test_returns_none_without_supported_markers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            profile = detect_project(Path(directory))

            self.assertIsNone(profile)


if __name__ == "__main__":
    unittest.main()
