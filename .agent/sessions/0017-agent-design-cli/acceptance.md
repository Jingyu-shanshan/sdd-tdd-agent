# Acceptance criteria

- [x] `agent design` uses the active Session and selected Provider protocol.
- [x] JSON and Codex protocols both reach `DESIGN_REVIEW` with valid output.
- [x] Success output is deterministic and exit code is 0.
- [x] Missing Session and invalid configuration fail before runner execution.
- [x] Workflow and adapter failures produce safe stderr and exit code 2.
- [x] Runner and Codex resolver remain injectable and testable.
- [x] Existing CLI commands and tests preserve their behavior.
- [x] No dependency or `.gitignore` update is required.
- [x] Active product Session remains unchanged.
