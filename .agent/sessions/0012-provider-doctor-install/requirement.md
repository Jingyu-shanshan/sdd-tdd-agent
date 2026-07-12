# Requirement

## User request

When a user selects an implemented Agent whose CLI is missing, offer to install
the current stable CLI and proceed only after explicit confirmation.

## Functional requirements

- Diagnose adapter lifecycle, CLI presence, and version health without mutation.
- Add `agent provider doctor [key]` with deterministic safe output.
- During interactive `provider use`, detect a missing implemented CLI and ask
  `[y/N]` before any download.
- Install only providers with an implemented Adapter and verified install plan.
- Download from the verified official URL into a private temporary directory.
- Execute download and installer as separate tokenized, shell-free processes.
- Re-locate the executable and verify `--version` before selecting the Provider.
- Preserve configuration and Session state on decline or any failure.

## Non-functional requirements

- No real installation, network download, or authentication occurs in tests.
- Installer, process runner, executable locator, and input are typed and mockable.
- No `sudo`, PATH mutation, credential collection, or implicit authentication.
- Errors redact installer stdout/stderr and downloaded content.
- Reuse the existing explicit analyzer timeout for bounded provider operations.

## Out of scope

- Installing planned Claude Code, Cursor, or Copilot Adapters.
- Automating Provider authentication.
- Windows installation.
- Silent installation in CI or other non-interactive environments.
