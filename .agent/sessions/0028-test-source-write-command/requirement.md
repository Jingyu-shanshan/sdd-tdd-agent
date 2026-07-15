# Requirement

## User request

Continue an IMPLEMENTATION Session by generating and safely writing exactly one
planned test file, as the first implementation behavior of `agent continue`.

## Requirements

- Load the configured active Session and selected Provider.
- Resume an existing `WRITE_TEST` cycle or atomically start the next eligible
  cycle without incrementing a resumed cycle.
- Deterministically collect bounded UTF-8 project source/config snapshots and
  the existing planned test file, excluding agent state, VCS data, caches,
  dependencies, hidden files, binaries, and symbolic links.
- Invoke the isolated single-test generator with dependency injection.
- Run Codex from an isolated temporary working directory outside the project so
  read-only tool access cannot reveal tasks, the full plan, or future tests.
- Validate and atomically write only the planned test path.
- Detect concurrent creation, deletion, or modification of the target test file
  between snapshot collection and write.
- Reject path traversal, protected roots, symbolic-link destinations, and
  leftover temporary-file collisions.
- Leave the cycle in `WRITE_TEST` after a successful write so RED must still be
  proven by the next stage.
- Add exact `agent continue` dispatch for this IMPLEMENTATION slice with safe,
  deterministic output and errors.
- Add an ignore rule for recoverable platform atomic-write temporary files.

## Out of scope

- Compiling or running the generated test.
- Recording RED evidence.
- Generating production code or proving GREEN.
- Dispatching `agent continue` for pre-IMPLEMENTATION workflow states.
