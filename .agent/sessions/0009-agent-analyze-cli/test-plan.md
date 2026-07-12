# Test plan

1. Config happy path: JSON command list, timeout, unrelated loop keys.
2. Composition: active ANALYSIS Session plus fake runner valid response.
3. CLI: exact success output and exit code with injected runner.
4. Config boundaries: missing/duplicate command, malformed/non-string item,
   missing/invalid timeout.
5. Project boundary: no active Session; runner must not be called.
6. Regression and final quality/package checks.

