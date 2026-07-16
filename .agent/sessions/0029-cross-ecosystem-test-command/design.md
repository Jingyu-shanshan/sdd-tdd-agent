# Design

`node_project.py` strictly loads root `package.json` and owns package-manager and
test-framework detection. `NodeProjectMetadata` is shared by general project
detection and test-command construction, avoiding divergent heuristics.

`test_execution.py` owns `TestCommandPlan` and `detect_test_command`. It selects
the ecosystem from the current planned test-file extension, validates the
single-test selector, and emits only a token tuple. No process boundary is
called.

Commands follow current primary documentation:

- Maven Surefire single-test selection:
  https://maven.apache.org/surefire-archives/surefire-2.21.0/maven-surefire-plugin/examples/single-test.html
- Gradle test filtering:
  https://docs.gradle.org/current/userguide/java_testing.html#test_filtering
- Jest CLI exact path/name filters: https://jestjs.io/docs/cli
- Vitest CLI and filtering: https://vitest.dev/guide/cli and
  https://vitest.dev/guide/filtering
- Angular CLI test options: https://angular.dev/cli/test
- npm/yarn test-script forwarding: https://docs.npmjs.com/cli/test/ and
  https://yarnpkg.com/cli/run

`project_detection.py` keeps Java precedence for its single-profile legacy API,
then reports a Node profile when no Java marker exists. Mixed-workspace command
detection remains extension-directed and therefore unambiguous.
