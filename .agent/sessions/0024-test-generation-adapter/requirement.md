# Requirement

## User request

Continue the SDD workflow by adding production JSON-command and Codex adapters
for the typed test-plan generator.

## Functional requirements

- Send all eight test-generation request fields through strict JSON stdin.
- Decode an exact four-field plan and exact eleven-field nested case objects.
- Reject invalid JSON, missing/extra keys, invalid scalar/list types,
  non-object cases, and non-string list members.
- Run Codex through one resolved executable using ephemeral read-only structured
  output with a strict nested JSON Schema.
- Use and clean a private temporary exchange directory.
- Report only safe error categories and process exit codes.

## Non-functional requirements

- Reuse existing typed runner, configuration, and Codex resolver contracts.
- Keep semantic plan validation and Session mutation in `test_generation`.
- Add no dependency, CLI, credential, model override, or environment mutation.
- Preserve the active PDF-export Session unchanged.

## Out of scope

- `agent tests` CLI orchestration.
- Test source generation or execution.
- Implementation and refactoring stages.
