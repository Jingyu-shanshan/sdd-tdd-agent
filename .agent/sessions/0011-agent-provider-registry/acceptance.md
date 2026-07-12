# Acceptance criteria

- [x] Registry distinguishes adapter-ready and planned providers.
- [x] Codex, Claude Code, Cursor, Copilot, and custom JSON appear honestly.
- [x] List/status output is deterministic and does not execute a provider.
- [x] Only fully configured adapter-ready providers can be selected.
- [x] Selection atomically updates only provider protocol/command.
- [x] Explicit timeout and unrelated configuration remain unchanged.
- [x] Invalid selection leaves configuration and Session state unchanged.
- [x] Existing analysis tests remain compatible.
- [x] `.gitignore` covers the atomic provider temporary artifact.
