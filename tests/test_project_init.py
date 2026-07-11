import tempfile
import unittest
from pathlib import Path

from sdd_tdd_agent.project_init import initialize_project


class InitializeProjectDirectoriesTest(unittest.TestCase):
    def test_creates_workspace_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            initialize_project(root)

            expected = {
                root / ".agent",
                root / ".agent" / "memories",
                root / ".agent" / "sessions",
                root / ".agent" / "cache",
                root / ".agent" / "logs",
                root / ".agent" / "metrics",
            }
            self.assertTrue(all(path.is_dir() for path in expected))


class InitializeProjectMetadataTest(unittest.TestCase):
    def test_creates_bootstrap_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            root = Path(parent) / "example-project"
            root.mkdir()

            initialize_project(root)

            workspace = root / ".agent"
            expected_files = {
                workspace / "config.yml",
                workspace / "project.yml",
                workspace / "architecture.md",
                workspace / "conventions.md",
            }
            self.assertTrue(all(path.is_file() for path in expected_files))
            self.assertIn(
                "name: example-project\n",
                (workspace / "project.yml").read_text(encoding="utf-8"),
            )

    def test_records_detected_java_build_tool(self) -> None:
        for marker, build_tool in (
            ("pom.xml", "maven"),
            ("build.gradle", "gradle"),
            ("build.gradle.kts", "gradle"),
        ):
            with self.subTest(marker=marker):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    (root / marker).touch()

                    initialize_project(root)

                    project_metadata = (root / ".agent" / "project.yml").read_text(
                        encoding="utf-8"
                    )
                    self.assertIn("target_language: java\n", project_metadata)
                    self.assertIn(f"build_tool: {build_tool}\n", project_metadata)


class ReinitializeProjectTest(unittest.TestCase):
    def test_preserves_existing_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialize_project(root)
            architecture = root / ".agent" / "architecture.md"
            architecture.write_text("# Team architecture\n", encoding="utf-8")

            initialize_project(root)

            self.assertEqual(
                "# Team architecture\n",
                architecture.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
