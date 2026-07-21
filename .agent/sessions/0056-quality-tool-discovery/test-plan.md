# Test plan

## RED

- Maven profiles recognize exact Checkstyle, SpotBugs, and PMD plugin
  coordinates while retaining JUnit 5 detection.
- Gradle Groovy/Kotlin plugin declarations recognize the same three tools.
- Node profiles require both dependencies and exact ESLint/Prettier script
  tokens, rejecting names that merely contain those strings.
- Detection order is canonical and `agent init` writes the non-empty list.
- Absent evidence produces an empty tuple and no metadata section.

## Regression

- Run focused project-detection, Node, and initialization tests.
- Run Ruff format/check, Pyright, all tests with coverage, and package build.
- Revalidate Session JSON, active Session bytes, secrets, changed-test scope,
  and ignored generated artifacts.
