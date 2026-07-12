# Acceptance criteria

- [x] Valid tracked config becomes immutable adapter configuration.
- [x] Active ANALYSIS Session is resolved and analyzed through injected runner.
- [x] `agent analyze` reports Session ID/state and exits 0.
- [x] Invalid config/no Session fails before runner execution and mutation.
- [x] Configuration and errors do not expose secrets or command values.
- [x] Production path remains shell-free.
- [x] Current real support-PDF Session remains unchanged during development.
- [x] Ruff, Pyright, pytest, coverage, packaging, and Python 3.9 checks pass.
