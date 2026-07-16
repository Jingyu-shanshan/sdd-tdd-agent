# Requirement

## User request

Continue the complete incremental SDD/TDD flow after a trustworthy GREEN by
starting the next planned test or closing implementation for review.

## Requirements

- Extend `agent continue` in GREEN without invoking a test runner.
- When another ordered test remains, start exactly that test's WRITE_TEST cycle
  through the existing isolated test-source generation path.
- Clear prior-cycle test, RED, production, GREEN, and verification-failure
  evidence when a new cycle starts.
- When no planned test remains, require the completed tests to cover the exact
  generated-plan prefix and validate the final GREEN evidence.
- Revalidate the final current-test and production-source ID/path/digests before
  leaving IMPLEMENTATION.
- Require exact tokenized current/full-suite commands, zero return codes, and
  already sanitized bounded stdout/stderr in final GREEN evidence.
- Atomically transition only IMPLEMENTATION to REVIEW, preserve audit evidence,
  clear `current_task`, and render deterministic CLI output.
- Preserve GREEN without model/process calls or mutation for stale, malformed,
  unsafe, or concurrently changed state and artifacts.
- Keep the real active user Session and unrelated files unchanged.

## Out of scope

- Performing code review.
- Automated or manual refactoring decisions.
- Transitioning REVIEW to REFACTOR or DONE.
- Adding new test cases after the approved generated plan is exhausted.
