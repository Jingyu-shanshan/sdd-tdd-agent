# Requirement

## User request

Continue the next complete roadmap task with SDD and incremental TDD, then
commit and push it without routine approval pauses.

## Requirements

- Add minimal real Maven and Gradle projects using JUnit Jupiter.
- Add minimal real npm, pnpm, and Yarn projects using Vitest and TypeScript.
- Make every fixture detectable by the existing project and command planners.
- Prove the exact single-test and full-suite commands generated for every
  fixture.
- Add automatic Ubuntu CI that installs and executes all five real toolchains.
- Use locked Node dependency graphs and immutable external Actions.
- Pin Java, Gradle, Node, npm, pnpm, Yarn, JUnit, Vitest, and Maven plugin
  versions to verified values.
- Keep CI permissions read-only and avoid shell-generated command selection.
- Do not present local simulation as real toolchain execution.
- Preserve the active user Session and update `.gitignore` if fixture tooling
  introduces generated paths not already covered.

## Out of scope

- Full production applications or framework migration.
- Angular CLI execution; Angular receives its own broader milestone.
- Windows, macOS, or Linux Mint toolchain execution in this increment.
- Provider adapter changes or new runtime dependencies for the Python package.
