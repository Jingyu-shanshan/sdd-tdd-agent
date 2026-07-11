# Conventions

- Production code lives in `sdd_tdd_agent/`.
- Tests live in `tests/` and use the standard-library `unittest` runner until a
  test requirement justifies another framework.
- Every production behavior starts with one failing test.
- Each TDD cycle covers one observable behavior and records RED/GREEN evidence
  in the active session's `implementation.md`.
- Tests are not weakened or rewritten merely to make production code pass.
- Public functions and CLI behavior use type hints and concise docstrings.

