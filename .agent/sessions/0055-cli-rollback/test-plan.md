# Test plan

## RED

- Prove a real repository restores only the current GREEN test and production
  paths, preserves HEAD and unrelated work, and resets the cycle to `WRITE_TEST`.
- Prove CLI output and exit status are deterministic and content-safe.
- Prove dirty target paths, non-Agent/mismatched HEAD, multi-parent metadata,
  incorrect commit paths, Git failures, and state collisions fail closed.
- Prove a failed state update restores target files from HEAD.

## Regression

- Run focused rollback and existing Git-integration tests.
- Run Ruff format/check, Pyright, all tests with coverage, and package build.
- Revalidate all Session JSON with duplicate-key rejection, preserve the active
  user Session exactly, scan for secrets, and audit ignored artifacts.
