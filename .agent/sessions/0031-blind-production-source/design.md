# Design

`production_source_generation.py` constructs a versioned request around
`BlindDevelopmentContext`. The request contains the current planned test, its
digest-bound source, production snapshots, and sanitized RED stdout/stderr.
Specification documents and the full test plan never enter this boundary.

`production_source_adapter.py` supplies strict JSON-command and Codex exec
adapters. Codex runs from a project-external temporary directory with a
read-only sandbox and exact three-field output Schema.

`production_source_workspace.py` collects only production files and owns an
optimistic-concurrency atomic writer for exactly one `src/**` source. A shared
path policy excludes test-like paths, hidden components, unsupported suffixes,
and symlinks.

`production_source_command.py` composes active Session lookup, strict Provider
configuration, Blind context loading, generation, final RED/artifact
revalidation, safe write, and the atomic RED -> IMPLEMENT state update.

`implementation_command.py` dispatches one step by phase:

```text
no source marker / WRITE_TEST -> generate test or execute RED
RED                           -> generate/write one production source
IMPLEMENT                     -> reserved for GREEN verification
```
