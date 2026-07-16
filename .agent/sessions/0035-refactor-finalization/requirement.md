# Requirement

## User request

Complete the core SDD/TDD state machine with a safe REFACTOR-stage final
verification and DONE transition.

## Requirements

- Add exact `agent refactor` behavior for the active REFACTOR Session.
- State honestly that v0.1 performs a no-source-change refactor verification;
  automated source refactoring remains deferred to v0.3.
- Validate the implementation-review record, canonical completion snapshot,
  actual `review.md` digest, retained GREEN evidence, and final source records.
- Revalidate final test and production file paths, symlink safety, and SHA-256
  digests before and after every external process.
- Execute the recorded exact current-test command first and recorded full-suite
  command second with their separate strict configured timeouts.
- Require both commands to exit zero. Preserve REFACTOR on any process,
  regression, signal, timeout, artifact, state, or concurrency failure.
- Persist only sanitized bounded final-verification evidence.
- Atomically record no-source-change refactor verification and transition only
  REFACTOR to DONE.
- Invoke no model and modify no source, test, SDD, dependency, or configuration
  file.
- Keep the real active user Session and unrelated files unchanged.

## Out of scope

- Automated semantic refactoring or source edits.
- Model-generated refactor suggestions.
- Git commit/push inside the product command.
- Rollback, release, deployment, or pull-request automation.
