# Test plan

1. Fake runner happy path: command, stdin JSON, timeout, typed analysis.
2. Process failures: non-zero exit and timeout without sensitive output leaks.
3. Schema failures: invalid JSON, non-object, missing/extra keys, invalid types.
4. Concrete runner: execute a controlled Python child with `shell=False`.
5. Configuration validation: empty command and non-positive timeout.
6. Regression: requirement workflow and all prior project/CLI tests.

