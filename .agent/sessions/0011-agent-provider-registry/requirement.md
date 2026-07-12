# Requirement

## User request

Add a selectable multi-provider foundation for Codex and future agents such as
Claude Code, Cursor, and GitHub Copilot, and formally plan Linux Mint support.

## Functional requirements

- Maintain a typed registry of adapter-ready and planned providers.
- List providers with deterministic status and platform information.
- Report the provider selected by current analyzer configuration.
- Select an adapter-ready provider through an explicit CLI command.
- Preserve unrelated configuration and the existing explicit timeout.
- Reject unknown, planned, or malformed selections without modifying files.

## Non-functional requirements

- Each workflow run continues to execute exactly one provider.
- Registry and configuration operations are typed and unit tested.
- Configuration writes are atomic and localized.
- No provider package, executable, or credential is installed or inferred.
- Existing analyzer protocols and the active real Session remain compatible.

## Out of scope

- Implementing Claude Code, Cursor, or GitHub Copilot adapters.
- Provider authentication or installation diagnostics.
- Linux CI provisioning; this increment records and enables the architecture.
