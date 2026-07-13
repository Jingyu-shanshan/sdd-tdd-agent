# Test plan

## JSON command adapter

- Verify exact tokenized command, timeout, seven-field stdin payload, and typed
  nested result.
- Reject invalid JSON, non-object top level, wrong top-level keys/types,
  non-list tasks, non-object task items, wrong task keys/scalars/list types, and
  non-string array members.
- Verify process errors expose only the exit code.

## Codex adapter

- Verify injected executable resolution and all safe `codex exec` flags.
- Inspect the emitted top-level and nested task JSON Schema.
- Verify structured result decoding and private directory cleanup.
- Reject command configurations with extra tokens.
- Verify process failure redaction and fixed missing-output errors.

## Quality

- Run targeted RED and GREEN tests before the full suite.
- Run Ruff format/check, Pyright, pytest with coverage, compile, and build.
- Verify Session JSON has no duplicate keys and `.gitignore` remains sufficient.
- Preserve the active PDF Session in `REQUIREMENT_REVIEW`.
