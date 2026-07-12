# Requirement

## User request

Continue Linux Mint adaptation with a real, testable platform contract instead
of assuming that all Linux environments behave like Linux Mint.

## Functional requirements

- Add `agent platform doctor` as a read-only diagnostic command.
- Detect macOS, Linux, and unsupported operating-system families.
- On Linux, parse standard `os-release` `ID` and `VERSION_ID` values.
- Classify `linuxmint` as the formal supported target.
- Classify other Linux distributions as compatible but not formally verified.
- Report Python >=3.9 support and temporary-directory availability.
- Return deterministic, sanitized diagnostic output.
- Reject malformed or duplicate `os-release` input safely.

## Non-functional requirements

- System access is typed, injected, mockable, and unit tested.
- Diagnosis never changes environment variables, PATH, configuration, or Session
  state.
- Use only the Python standard library and existing dependencies.
- Production temporary probes clean up automatically.

## Out of scope

- Provisioning a Linux Mint VM or CI runner.
- Installing Java, Node.js, package managers, or Agent CLIs.
- Declaring every Linux distribution formally supported.
- Windows platform implementation.
