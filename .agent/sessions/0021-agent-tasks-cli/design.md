# Design

## Application service

Add `task_command.py` with `generate_active_tasks(root, runner,
command_resolver=None)`. The service loads project status first and fails before
configuration or process execution when there is no active Session. It then
loads the existing analyzer configuration and chooses exactly one adapter:

```text
json-command -> JsonCommandTaskBreakdownGenerator
codex-exec   -> CodexExecTaskBreakdownGenerator
```

The selected adapter is passed to `run_task_breakdown`; no Session rules are
reimplemented in the service.

## CLI composition

The exact argument vector `agent tasks` constructs the injected or default
process runner, calls the application service, and renders:

```text
Tasks ready for review: <session-id> (TASK_REVIEW)
```

`ValueError` and the existing safe model-adapter error hierarchy are rendered
using the established `Error: ...` contract with exit code 2.

## Safety

The command inherits strict configuration parsing, tokenized `shell=False`
execution, Codex read-only ephemeral behavior, output redaction, full task
validation, and atomic artifact/state writes from existing layers.
