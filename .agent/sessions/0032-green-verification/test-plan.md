# Test Plan

- Prove exact full-suite commands for Maven/Gradle/Jest/Vitest/Angular and all
  supported package-manager prefixes.
- Prove missing, duplicate, nonnumeric, nonfinite, zero, and negative suite
  timeouts fail safely.
- Prove changed/stale/missing/symlinked test or production artifacts prevent
  process execution and state mutation.
- Prove current-test pass runs the suite; current-test failure never does.
- Prove attributable current failure and nonempty valid regression failure
  return to RED with sanitized bounded evidence.
- Prove pass, signal, timeout, start failure, no-test, bad-option, empty, and
  unrelated current output preserve expected state.
- Prove suite signal/no-test/bad-option/empty outcomes preserve IMPLEMENT.
- Prove state/file changes during either process prevent GREEN.
- Prove both passes append exactly the current test, set GREEN, and record both
  exact commands with sanitized output.
- Prove IMPLEMENT `agent continue` never calls a model and prints deterministic
  GREEN output.
