# Design

## Adapter boundary

Add `test_adapter.py` as a transport-only implementation of
`TestPlanGenerator`. It imports established request/result models but reads or
mutates no Session files.

## Strict structure

The top-level Schema requires exactly `summary`, `cases`, `risks`, and
`open_questions`. Every case requires exactly test/task IDs, phase, title,
objective, target file/name, preconditions, action, expected outcomes, and
dependencies. Additional properties are forbidden at both object levels.

## Codex exchange

Use the established safe command contract:

```text
codex exec --ephemeral --sandbox read-only --color never
  --output-schema <schema> --output-last-message <output>
  --cd <workspace> -
```

The configured executable is resolved through injection; model, authentication,
and environment remain user-controlled.

## Failure policy

Malformed output raises `TestPlanGeneratorError`. Process failures expose only
the exit code, and missing/unreadable Codex output uses a fixed message. Prompt,
request, stdout, stderr, and filesystem content are never included.
