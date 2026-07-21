# Requirement

## Goal

Extend fresh project initialization with evidence-based discovery of the
quality tools named by the original Java and TypeScript design.

## Requirements

- Detect Maven Checkstyle, SpotBugs, and PMD only from exact build-plugin
  coordinates.
- Detect Gradle Checkstyle, SpotBugs, and PMD only from exact plugin declarations.
- Detect ESLint and Prettier only when package metadata contains both the tool
  dependency and a script that invokes its exact command token.
- Keep tool order deterministic and persist non-empty results in tracked
  `project.yml` as `quality_tools`.
- Preserve existing language, build-tool, test-framework, validation, and
  write-once initialization behavior.

## Non-goals

- Installing or executing quality tools.
- Inventing commands when project configuration is absent.
- Parsing subprojects, custom Gradle logic, or non-root build metadata.
