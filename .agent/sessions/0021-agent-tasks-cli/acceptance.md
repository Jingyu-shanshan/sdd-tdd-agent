# Acceptance criteria

- [x] The service requires a configured active Session.
- [x] JSON configuration selects the JSON task adapter.
- [x] Codex configuration selects the Codex task adapter and injected resolver.
- [x] Valid output writes `tasks.md` and enters `TASK_REVIEW`.
- [x] `agent tasks` prints the deterministic success message.
- [x] Configuration and workflow errors return 2 with safe stderr output.
- [x] No runner executes when active Session or configuration is invalid.
- [x] Existing task semantic and approval validation remains authoritative.
- [x] Existing behavior and the active product Session remain unchanged.
- [x] No dependency or unnecessary `.gitignore` update is introduced.
