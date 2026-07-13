# Design

## Adapter boundary

Add `task_adapter.py` as a transport-only implementation of the existing
`TaskBreakdownGenerator` Protocol. It imports the established request and
result models but does not read or mutate Session files.

## Provider-neutral JSON protocol

`JsonCommandTaskBreakdownGenerator` serializes exactly the request fields and
passes them to the injected tokenized runner. A successful response must have
the exact top-level fields `summary`, `tasks`, `global_risks`, and
`open_questions`. Each task must have the exact domain-model fields and all list
members must be strings.

## Codex protocol

`CodexExecTaskBreakdownGenerator` resolves one configured executable and uses:

```text
codex exec --ephemeral --sandbox read-only --color never
  --output-schema <private schema> --output-last-message <private output>
  --cd <workspace> -
```

The nested Schema disallows additional properties at both breakdown and task
levels. Configuration does not override model, authentication, or user state.

## Failure policy

Malformed responses raise a task-generator-specific safe error. Process
failures expose only the exit code. Missing/unreadable Codex output exposes a
fixed message. Request, stdout, stderr, Prompt, and filesystem contents are
never copied into errors.
