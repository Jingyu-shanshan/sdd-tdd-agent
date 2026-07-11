# Requirement: Initialize an agent workspace

## Description

Add the first MVP command, `agent init`. It initializes the hidden workspace
that future SDD sessions, memories, logs, and metrics will use inside a target
project.

## User story

As a developer adopting the platform, I want to run `agent init` in my project
so that it has the standard files and directories required by later commands.

## Functional requirements

- Initialization creates `.agent/` below the selected project root.
- It creates `memories/`, `sessions/`, `cache/`, `logs/`, and `metrics/`.
- It creates `config.yml`, `project.yml`, `architecture.md`, and
  `conventions.md` with usable bootstrap content.
- `project.yml` records the target directory name as the project name.
- `agent init` initializes the current working directory, reports
  `Initialized .agent workspace.`, and exits with status 0.
- Re-running initialization succeeds without overwriting existing metadata.

## Non-functional requirements

- No runtime third-party dependency is introduced.
- File creation is deterministic and testable with a temporary directory.
- Initialization does not inspect or modify source files.

## Deferred scope

- Maven, Gradle, npm, pnpm, and yarn detection.
- Dependency, module, test-framework, and coding-style scanning.
- Updating an existing workspace to a newer schema.
- Recovering a partially invalid workspace.

