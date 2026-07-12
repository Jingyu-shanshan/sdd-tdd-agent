# Requirement

## User request

Provide a built-in Codex CLI bridge so `agent analyze` can use the locally
installed Codex executable instead of requiring an unspecified external model
bridge.

## Functional requirements

- Add an explicit `codex-exec` analyzer protocol while preserving the existing
  `json-command` protocol.
- Invoke `codex exec` without a shell and with the configured timeout.
- Require ephemeral, read-only execution and a strict JSON output schema.
- Read the final structured result from a temporary output file and pass it
  through the existing domain validation.
- Configure the repository to use the `codex` executable explicitly.
- Return safe errors without exposing prompts, model output, or credentials.

## Non-functional requirements

- All model/process interactions remain typed, injected, mockable, and tested.
- Use only the Python standard library and existing dependencies.
- Preserve the current real feature Session until a user intentionally runs
  analysis.

## Out of scope

- Running a real paid/model-backed requirement analysis during development.
- Selecting or overriding the user's Codex model or authentication.
- Supporting additional provider-specific protocols in this increment.
