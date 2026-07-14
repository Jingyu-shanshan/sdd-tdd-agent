# Requirement

## User request

Continue the SDD workflow by exposing active-Session task breakdown through the
CLI and currently configured Provider protocol.

## Functional requirements

- Add an application service that resolves the configured active Session.
- Load the existing strict analyzer command, timeout, and protocol settings.
- Select the JSON command or Codex task-breakdown adapter from that protocol.
- Delegate all approval, state, context, output, dependency, and filesystem
  validation to the existing task-breakdown workflow.
- Add the exact `agent tasks` CLI command.
- On success, report the Session ID and `TASK_REVIEW` state.
- On configuration, active-Session, adapter, or workflow failure, write a safe
  error to stderr and return exit code 2.

## Non-functional requirements

- Keep the runner and Codex command resolver injectable and mockable.
- Reuse existing configuration and Provider behavior without new dependencies.
- Do not duplicate Session or task validation in CLI dispatch.
- Preserve all existing commands and public behavior.
- Preserve the active PDF-export Session unchanged.

## Out of scope

- Task show, approve, or reject commands.
- Automatic transition beyond `TASK_REVIEW`.
- Test generation or implementation execution.
- New Provider, installation, authentication, or configuration formats.
