# Acceptance criteria

- [x] Adapter request/response and runner boundaries are typed and immutable.
- [x] Exact JSON input is delivered through an injected runner.
- [x] Valid output becomes `RequirementAnalysis`.
- [x] Process and schema failures return safe dedicated errors.
- [x] Production execution never invokes a shell.
- [x] No request/process content leaks through errors.
- [x] Current support-PDF Session remains unchanged.
- [x] Ruff, Pyright, pytest, coverage, packaging, and Python 3.9 checks pass.
