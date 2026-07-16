# Requirement

## User request

Detect a deterministic command that executes only the current planned test
across Java, TypeScript, and Angular projects without running it yet.

## Requirements

- Produce a typed immutable command plan containing ecosystem, build/package
  tool, framework, test file/name, and tokenized command.
- Never invoke a shell or process during detection.
- Support Maven Surefire single class/method selection.
- Support Gradle `Test` filtering by fully qualified class and method.
- Prefer executable Maven/Gradle wrappers; use `sh <wrapper>` for a present
  non-executable POSIX wrapper; otherwise use the system command name.
- Parse Java/Kotlin test paths under standard test-source roots into fully
  qualified class names and reject non-standard/unsafe paths and names.
- Strictly parse `package.json` with duplicate-key rejection.
- Detect npm, pnpm, or yarn from the `packageManager` field or exactly one
  matching lockfile; reject conflicts and missing evidence.
- Require a configured `test` script and detect Angular, Jest, or Vitest from
  verified project markers, dependencies, and script content.
- Build one-file/one-name commands using the project's test script:
  - Jest: exact path and name pattern, serial execution.
  - Vitest: non-watch run, file filter, and name pattern.
  - Angular: non-watch `ng test` with exact include and name filter.
- Select Java or Node handling from the planned test-file extension so mixed
  workspaces do not silently choose the wrong root marker.
- Reject null bytes, path traversal, unsupported extensions/frameworks, invalid
  package metadata, missing test scripts, and ambiguous tool selection.
- Extend root project detection to report TypeScript/Angular profiles using the
  same strict Node metadata.
- Keep `.gitignore` unchanged unless verification creates a new unignored
  artifact class.

## Out of scope

- Locating or installing Maven, Gradle, Node, or package-manager executables.
- Executing the command or interpreting output.
- Recording RED/GREEN state or evidence.
- Monorepo/workspace package selection beyond the root `package.json`.
