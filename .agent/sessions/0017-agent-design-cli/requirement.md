# Requirement

## User request

Continue the design workflow by exposing the configured active-Session design
generation through `agent design`.

## Functional requirements

- Resolve the active Session from tracked project metadata.
- Reuse the selected Provider protocol, tokenized command, and timeout from the
  existing strict analyzer configuration.
- Construct the JSON command or Codex exec design generator for that protocol.
- Invoke the typed design-generation workflow.
- On success, print the Session identifier and `DESIGN_REVIEW`, then return 0.
- On missing Session, invalid configuration, wrong workflow state, invalid
  output, or process failure, print a safe `Error:` line to stderr and return 2.
- Retain runner and Codex executable-resolver injection for tests.

## Non-functional requirements

- CLI dispatch remains thin and contains no model, state, or filesystem logic.
- No real model command runs in tests.
- Errors do not expose Prompt, project context, output, credentials, or command
  values.
- Use only existing dependencies and Provider configuration.
- Preserve `agent analyze` and all existing command behavior.
- Do not change the active real PDF-export Session.

## Out of scope

- Design approval/rejection commands.
- New per-stage Provider settings.
- Automatic requirement approval.
- Task breakdown after `DESIGN_REVIEW`.
