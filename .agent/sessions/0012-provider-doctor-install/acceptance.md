# Acceptance criteria

- [x] Doctor distinguishes installed, missing, unhealthy, and planned Providers.
- [x] Doctor never mutates configuration or Session state.
- [x] Missing CLI triggers a prompt only in an interactive terminal.
- [x] Default answer and explicit rejection perform no install or selection.
- [x] Confirmation uses only the Registry's verified official install plan.
- [x] Download and execution are separate shell-free commands.
- [x] Successful install is re-located and version-verified before selection.
- [x] Failures redact process content and preserve configuration/Session state.
- [x] Planned or command-less Providers are never downloaded.
- [x] Unsupported-platform installation is rejected before prompting/download.
- [x] No real download, install, or authentication occurs in tests.
