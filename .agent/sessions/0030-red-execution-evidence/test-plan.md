# Test Plan

- Prove generated-source marker records exact ID/path/SHA-256 and a new cycle
  clears old source/RED evidence.
- Prove a valid non-zero assertion failure referencing current test transitions
  only WRITE_TEST to RED and persists the exact token command.
- Prove a compilation failure referencing the current test is valid RED.
- Prove zero, negative, timeout, start failure, no-test, unknown-option, empty,
  and unrelated non-zero output do not mutate state.
- Prove source digest changes before or during execution fail without RED.
- Prove evidence removes ANSI/control sequences, root paths, tokens, passwords,
  API keys, authorization/bearer values, and truncates oversized streams.
- Prove timeout config rejects missing, duplicate, nonnumeric, nonfinite, zero,
  and negative values.
- Prove first `agent continue` still generates a test and second continue executes
  RED with deterministic CLI output.
- Prove model runner is not called during RED and test runner is not called
  during test generation.
