# Design

`test_source_workspace.py` provides two injected boundaries:

- `WorkspaceSourceCollector` reads a deterministic, bounded set of source files
  rooted under `src/`, selected root build/config markers, and the exact planned
  test file.
- `AtomicTestSourceWriter` validates the generated source again, compares the
  target against its captured snapshot, rejects symlink ancestors, writes an
  exclusive `*.agent.tmp` sibling, and atomically replaces the destination.

`prepare_write_test_cycle` in `tdd_cycle.py` resumes `WRITE_TEST`, starts a new
cycle only from no progress or GREEN, and rejects RED/IMPLEMENT.

`test_source_command.py` composes active Session lookup, strict configuration,
cycle preparation, source collection, Test Context loading, provider selection,
generation, and writing. For `codex-exec`, it creates a separate temporary
working directory and passes that to the already read-only adapter; project
content is visible only through the typed request snapshots.

The exact CLI vector `agent continue` renders:

```text
Test source ready for RED: feature-1 (TC1 -> tests/test_export.py)
```
