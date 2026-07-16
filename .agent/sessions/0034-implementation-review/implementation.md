# Implementation

## RED

Added focused tests for completion snapshots, canonical evidence digests,
deterministic report content, REVIEW -> REFACTOR state, CLI output, state/report
tampering, symlinks, missing/oversized artifacts, and both atomic temporary
collisions. The first targeted run failed during collection because the review
module did not exist.

## GREEN

Bound REVIEW entry to exact completed IDs and final evidence/artifact digests.
Implemented a deterministic invariant-review service that validates the
retained snapshot, writes no source or process output, explicitly defers
semantic automated review, records report/completion digests, and enters only
REFACTOR. The exact CLI command invokes no model, test runner, or process.

During GREEN hardening, a new collision-preservation assertion exposed that
cleanup could delete a temporary marker owned by another process. Temporary
ownership is now tracked explicitly, so only files created by the current
review attempt are removed.

## Verification

- Ruff lint and formatting passed.
- Pyright passed with zero errors or warnings.
- Pytest passed: 618 tests, 93.94% total coverage.
- The new critical implementation-review module has 94% coverage.
- Source distribution and wheel builds passed; Python bytecode compilation
  passed.
- Existing `.gitignore` covers build/cache/bytecode/coverage and both review
  atomic temporary paths, so no update was needed.
- All Session JSON parsed, no credential-shaped values were introduced, and
  the active PDF Session remained unchanged in `REQUIREMENT_REVIEW`.
