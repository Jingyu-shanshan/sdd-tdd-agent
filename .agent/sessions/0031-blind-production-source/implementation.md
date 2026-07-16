# Implementation

## RED

Added focused tests for Blind context isolation, RED evidence and test-source
binding, strict production result/path validation, JSON/Codex adapters,
production-only collection, optimistic atomic writes, RED -> IMPLEMENT state,
and `agent continue` dispatch. The first targeted run failed during collection
because all four production-source modules were absent.

## GREEN

Implemented the versioned production Prompt, typed Blind request/result,
provider-neutral JSON and project-external read-only Codex adapters, bounded
production collector, and single-file atomic writer. The orchestration
revalidates current test/state around the model and write, records only the
production ID/path/SHA-256, and advances exactly RED to IMPLEMENT. The model
payload contains no SDD documents, full plan, future tests, or raw Session.

## Verification

- Ruff lint and formatting passed.
- Pyright passed with zero errors or warnings.
- Pytest passed: 531 tests, 94.25% total coverage.
- New critical modules cover 100%, 90%, 94%, and 90% respectively.
- Package source distribution and wheel built with the new Prompt included.
- Python bytecode compilation passed.
- Existing `.gitignore` covers build/cache/bytecode/coverage and both atomic
  temporary patterns; no update was needed.
- All Session JSON parsed, no credential-shaped values were introduced, and the
  active PDF Session remained unchanged in `REQUIREMENT_REVIEW`.
