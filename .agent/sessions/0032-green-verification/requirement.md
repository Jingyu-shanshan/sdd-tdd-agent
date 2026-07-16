# Requirement

## User request

Continue the full incremental SDD/TDD workflow by verifying the generated
production change reaches GREEN without hiding regressions or trapping a failed
implementation.

## Requirements

- In IMPLEMENT, revalidate the current test ID/path/digest and the recorded
  production source ID/path/digest before and after every external process.
- Detect a shell-free full-suite command for Maven/Gradle JUnit 5 and npm/pnpm/
  yarn projects using Jest, Vitest, or Angular.
- Load a separate required positive finite
  `full_test_suite_timeout_seconds`; never infer it from model or single-test
  timeouts.
- Run exactly the current test first. Run the full suite only after it passes.
- Treat signal, timeout, start, no-test, bad-option, empty, and unattributed
  current-test failures as infrastructure errors and preserve IMPLEMENT.
- When the current test produces a trustworthy positive non-zero failure,
  atomically return IMPLEMENT to RED with sanitized retry evidence so the Blind
  generator can make another minimal attempt.
- When the current test passes but the full suite produces a trustworthy
  positive non-zero failure, atomically return to RED with sanitized regression
  evidence for a minimal compatibility fix.
- Treat full-suite pass only as return code zero; reject signal, no-test,
  bad-option, or empty non-zero output without mutation.
- Only after both commands pass, atomically set GREEN, append the current test
  to the ordered completed prefix, and record bounded sanitized command/output
  evidence.
- Extend `agent continue` so IMPLEMENT invokes no model and renders
  deterministic success/error output.
- Preserve the active user Session, unrelated files, existing tests, and public
  commands.

## Out of scope

- Review/refactor automation.
- Starting the next test cycle or marking the entire Session DONE.
- Test retries, flaky-test suppression, coverage enforcement in target projects,
  or dependency/toolchain migration.
