# Test plan

1. Maven happy path using an empty temporary `pom.xml`.
2. Gradle happy paths using subtests for `.gradle` and `.gradle.kts` markers.
3. Integration: initialize a fresh Maven project and inspect `project.yml`.
4. Regression: all prior init and CLI tests remain GREEN.

Build-file content parsing, conflicts, nested projects, and test-framework
detection are outside this session.

