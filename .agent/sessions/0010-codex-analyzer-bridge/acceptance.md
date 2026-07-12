# Acceptance criteria

- [x] `codex-exec` builds the verified local Codex CLI invocation.
- [x] The request is sent through stdin and the response uses a strict schema.
- [x] Execution is ephemeral, read-only, shell-free, and timeout-bounded.
- [x] Invalid configuration and failed/missing output fail safely.
- [x] Existing `json-command` integrations remain compatible.
- [x] `agent analyze` is fully configured without embedding credentials.
- [x] No real model request occurs in automated tests.
- [x] The current real feature Session remains in `ANALYSIS` during development.
- [x] A macOS terminal without the ChatGPT resource PATH can start bundled Codex.
- [x] Custom configured executable names never use the platform fallback.
