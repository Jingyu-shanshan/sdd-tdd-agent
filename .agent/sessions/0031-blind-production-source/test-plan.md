# Test Plan

- Prove the Blind request contains current test plan/source, production source,
  and sanitized output but no requirement/design/tasks/full plan/future tests.
- Prove missing, stale, dirty, oversized, or mismatched RED evidence/test source
  fails without calling a model or mutating state.
- Prove production collection excludes current/other tests, hidden files,
  symlinks, build output, and unsupported files.
- Prove generated output requires exact fields, current ID, one safe production
  path, bounded content, and no null bytes.
- Prove JSON and Codex adapters use typed payloads, strict Schema, shell-free
  injected runners, and project-external temporary workspaces.
- Prove safe creation and optimistic replacement; reject traversal, tests,
  configuration, symlink, stale target, and temporary collision writes.
- Prove successful state transition records ID/path/digest and IMPLEMENT, while
  failures preserve RED and existing source/state.
- Prove RED `agent continue` invokes only the model boundary and prints
  deterministic production-source output.
- Prove a new cycle clears stale production-source evidence.
