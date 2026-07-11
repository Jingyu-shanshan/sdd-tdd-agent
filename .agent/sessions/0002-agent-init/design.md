# Design: Initialize an agent workspace

## Components

- `sdd_tdd_agent.project_init.initialize_project(root)` owns filesystem
  initialization independently of the CLI.
- `sdd_tdd_agent.cli.main(...)` dispatches `init`, supplies the working
  directory, writes the success message, and maps success to exit code 0.

## Data flow

```text
agent init -> CLI cwd -> initialize_project -> .agent tree -> success output
```

## Write policy

Directories use `mkdir(parents=True, exist_ok=True)`. Metadata files use
exclusive first-write semantics so a second run preserves user edits.

## Risks and controls

- Accidental overwrite of project knowledge: never replace existing files.
- Tests touching the repository: inject a temporary project root.
- Premature project detection abstractions: defer until detection has its own
  failing test.

