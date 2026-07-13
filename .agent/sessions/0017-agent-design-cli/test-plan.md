# Test plan

## Composition

- Run an approved DESIGN Session through a fake JSON command and verify command,
  request, design artifact, and DESIGN_REVIEW state.
- Run the same workflow through Codex protocol and verify resolver/exec usage.
- Reject a project without an active Session before touching configuration or
  the runner.

## CLI

- Verify exact success output and exit code 0.
- Verify incomplete configuration produces one safe stderr line and exit code 2.
- Verify state and adapter errors use the same error boundary.

## Regression and quality

- Run all tests with coverage, Ruff format/check, and Pyright.
- Compile and build source/wheel packages.
- Validate all Session JSON without duplicate keys.
- Review `.gitignore` and preserve the active PDF Session.
