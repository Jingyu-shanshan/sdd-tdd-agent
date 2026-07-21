# Requirement

## Goal

Publish the complete implemented target-language, toolchain, and test-framework
matrix from the original design as a typed deterministic capability Registry.

## Acceptance criteria

- Java reports Maven, Gradle, and JUnit 5 support.
- TypeScript reports npm, pnpm, Yarn, Jest, Vitest, and Angular support.
- `agent ecosystem list` is deterministic and read-only.
- The Registry is explicit about supported status and does not claim
  undocumented languages or frameworks.
- Existing detection, incremental TDD, Angular, and real-toolchain behavior
  remains unchanged.

## Out of scope

- Python, Go, Rust, or other languages not named by the original design.
- Adding a framework without detection, command, and real-fixture evidence.
- Dynamic executable or dependency discovery during capability listing.
