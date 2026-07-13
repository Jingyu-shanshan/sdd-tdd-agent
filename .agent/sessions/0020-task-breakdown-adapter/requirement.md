# Requirement

## User request

Continue the SDD workflow by adding production model adapters for the typed
task-breakdown generator.

## Functional requirements

- Send all seven task-breakdown request fields through a provider-neutral JSON
  stdin protocol.
- Decode an exact four-field breakdown object and exact seven-field nested task
  objects into the existing immutable domain models.
- Reject invalid JSON, non-object responses, missing or extra fields, invalid
  scalar types, invalid array types, non-object task entries, and non-string
  array members.
- Run Codex through one resolved executable with ephemeral, read-only,
  shell-free execution and a strict nested JSON Schema.
- Read Codex structured output from a private temporary exchange directory and
  remove the directory after every outcome.
- Report only safe failure categories and process exit codes.

## Non-functional requirements

- Reuse the existing typed process runner, configuration, and Codex resolver
  contracts through dependency injection.
- Keep task semantic and Session mutation rules in the existing workflow.
- Add no dependency, credential storage, model override, environment mutation,
  CLI command, or Provider selection behavior.
- Preserve the active PDF-export Session unchanged.

## Out of scope

- `agent tasks` CLI orchestration.
- Task approval or rejection commands.
- Test generation and implementation execution.
- New Provider implementations or Provider installation behavior.
