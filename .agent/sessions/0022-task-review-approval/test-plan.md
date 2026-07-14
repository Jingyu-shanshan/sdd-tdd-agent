# Test plan

## Review domain

- Load the active task artifact in `TASK_REVIEW` without changing state.
- Approve and verify exact preserved state plus `task_review` record.
- Reject with whitespace-normalized reason and verify return transition.
- Reject wrong state, mismatched identity, non-object state, missing prior
  approvals, empty/non-generated tasks, and empty rejection reason.
- Verify every invalid decision leaves state byte-for-byte unchanged.

## Safe filesystem failures

- Cover missing project/session, malformed JSON, and missing task artifact with
  review-specific safe errors.

## CLI

- Verify exact output and exit codes for show, approve, and reject.
- Verify empty rejection reason is reported to stderr with exit code 2.

## Quality

- Run targeted RED and GREEN tests before the full suite.
- Run Ruff format/check, Pyright, pytest with coverage, compile, and build.
- Verify Session JSON has no duplicate keys and `.gitignore` remains sufficient.
- Preserve the active PDF Session in `REQUIREMENT_REVIEW`.
