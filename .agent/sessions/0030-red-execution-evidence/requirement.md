# Requirement

## User request

Continue the incremental TDD flow by executing the generated current test and
recording RED only when its failure is trustworthy and attributable.

## Requirements

- After writing one generated test, atomically record its test ID, planned path,
  and SHA-256 digest in Session state without storing source content.
- Clear stale source/RED evidence when a new TDD cycle starts.
- Extend `agent continue` so a current matching source artifact executes RED;
  otherwise it retains the existing test-generation behavior.
- Load a required positive finite `test_command_timeout_seconds` setting.
- Execute the tokenized command plan with `shell=False`, project-root cwd,
  captured output, an explicit timeout, and an injected typed runner.
- Treat return code zero as an unexpected pre-implementation pass and keep
  `WRITE_TEST` unchanged.
- Reject process start failure, timeout, signal termination, unsupported/no-test
  output, and non-zero output that cannot be attributed to the current test.
- Accept assertion or compilation failure only when output references the exact
  test path, filename, test name, or Java test class.
- Revalidate phase, test identity, and source digest after execution before
  mutation so concurrent Session/source changes cannot be recorded as RED.
- Sanitize evidence before persistence: remove ANSI/control data, replace the
  project root, redact common credential fields and bearer tokens, and bound
  stdout/stderr sizes.
- Atomically transition only the current cycle from `WRITE_TEST` to `RED` and
  record command, return code, and sanitized output in top-level `red_evidence`.
- Produce deterministic CLI success/error text without traceback or sensitive
  process content.
- Add the timeout setting to new-workspace defaults and this repository's
  tracked configuration.
- Recheck `.gitignore`; add nothing unless execution creates a new artifact
  class outside existing build/cache rules.

## Out of scope

- Generating or writing production code.
- Re-running the test for GREEN or running the full suite.
- Framework-specific parsing of every possible diagnostic format.
- Persisting raw or unbounded process output.
