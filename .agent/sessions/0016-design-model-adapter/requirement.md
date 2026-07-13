# Requirement

## User request

Continue the design workflow by adapting the existing provider-neutral JSON
command and Codex exec protocols to the typed `DesignGenerator` boundary.

## Functional requirements

- Add a strict JSON command design generator using the existing tokenized
  process runner and validated command/timeout configuration.
- Add a Codex exec design generator using a strict design JSON Schema.
- Send the complete typed design request through stdin as JSON.
- Decode exactly the ten design fields into `DesignProposal`.
- Run Codex ephemerally in a read-only sandbox and write final structured output
  to a private temporary file.
- Resolve the configured Codex executable through the existing injected
  resolver.
- Return deterministic errors without exposing request, stdout, stderr,
  temporary content, credentials, or paths.

## Non-functional requirements

- All process execution remains typed, injected, mockable, and `shell=False`.
- The design workflow and Session filesystem remain outside the adapter.
- No model, authentication, user configuration, or environment variable is
  overridden.
- Use only the Python standard library and existing dependencies.
- Preserve existing requirement-adapter behavior and all active Session state.

## Out of scope

- `agent design` CLI orchestration.
- New provider configuration keys.
- Real model-backed execution during tests.
- Design approval and task breakdown.
