# Design

## Fixture boundary

Store five isolated projects under `tests/fixtures/toolchains/`. Maven and
Gradle each compile one Java class and execute one JUnit Jupiter test. npm,
pnpm, and Yarn each execute the same small TypeScript behavior with real Vitest.
Each Node fixture owns exactly one package-manager declaration and lockfile so
the production detector cannot confuse managers.

## Planner contract

Python tests load fixture paths through `detect_project`,
`detect_test_command`, and `detect_full_test_command`. Expected commands match
the actual commands used by CI:

- `mvn test`
- `gradle test`
- `npm test -- --run`
- `pnpm test -- --run`
- `yarn run test --run`

Single-test assertions also prove exact file and test-name filters.

## Remote execution

Create a separate `Toolchain fixtures` workflow on Ubuntu 24.04. The Java job
uses a Maven/Gradle matrix with Temurin Java 21 and a pinned Gradle distribution.
The Node job uses an npm/pnpm/Yarn include matrix with pinned Node and manager
versions. Installation and test steps stay explicit per manager so matrix data
never becomes a dynamically assembled shell command.

## Supply chain

All external Actions use full verified commit SHAs. Direct and transitive Node
dependencies are committed as manager-specific lockfiles. Maven and Gradle use
fixed plugin and library versions. Workflow permissions expose repository
contents as read-only.

## Evidence boundary

Local tests validate fixture structure and command planning. Only a successful
GitHub-hosted run counts as real execution evidence because the development Mac
does not have all five usable toolchains.
