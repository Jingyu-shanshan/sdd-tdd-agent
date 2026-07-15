# Requirement

## User request

Expose active-Session test-plan generation through the configured Provider.

## Requirements

- Resolve the configured active Session and strict command/protocol settings.
- Select JSON-command or Codex test-plan adapter.
- Delegate all approvals, state, semantic validation, and mutation to the core.
- Add the exact `agent tests` command.
- Report Session ID and `IMPLEMENTATION` on success.
- Use safe stderr and exit code 2 on known failures.
- Keep runner/resolver injectable; add no dependency or Provider behavior.
- Preserve the active PDF Session unchanged.

## Out of scope

- Writing/running tests and production implementation.
- Plan review commands.
