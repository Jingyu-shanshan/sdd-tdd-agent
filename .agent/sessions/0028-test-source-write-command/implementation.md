# Implementation

## RED

Three new test modules failed collection because cycle preparation, workspace
source/write boundaries, and the active command did not exist. After the first
GREEN implementation, three newly added command fixtures exposed positional
argument mistakes that passed progress dictionaries as Provider protocols; only
the fixture calls were corrected to use explicit `progress=` arguments.

## GREEN

Added recoverable cycle preparation, bounded deterministic source collection,
optimistic-concurrency atomic writing, exact `agent continue` dispatch, and
active JSON/Codex orchestration. Codex uses a project-external temporary working
directory. The generated file is written while state remains `WRITE_TEST`.

Added an independent failure-path test module to raise the security-critical
writer/collector coverage above 90% without changing existing tests.

## Verification

All 32 increment tests pass. The full 375-test suite passes at 94.48% coverage;
`tdd_cycle.py` and `test_source_workspace.py` are both 91%, and
`test_source_command.py` is 97%. Ruff, Pyright, compile, build, Session JSON,
active-Session preservation, and ignore-rule checks pass.
