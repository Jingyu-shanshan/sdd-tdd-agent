# Acceptance criteria

- [x] JSON commands receive all and only the typed request fields.
- [x] Valid nested responses decode into immutable breakdown/task models.
- [x] Missing/extra keys and every invalid nested type are rejected.
- [x] Codex receives a strict nested Schema with no additional properties.
- [x] Codex runs ephemerally, read-only, shell-free, and in the target workspace.
- [x] Temporary schema/output files are removed after execution.
- [x] Errors do not expose request, stdout, stderr, or sensitive content.
- [x] Existing workflow semantic validation remains authoritative.
- [x] Existing behavior and the active product Session remain unchanged.
- [x] No dependency or unnecessary `.gitignore` update is introduced.
