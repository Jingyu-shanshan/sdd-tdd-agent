# Test plan

## Unit tests

- Load active requirement Markdown and state into an immutable review context.
- Approve and reject from `REQUIREMENT_REVIEW` while preserving other keys.
- Normalize and persist a rejection reason.
- Reject empty reasons, wrong states, missing active Sessions, mismatched Session
  identifiers, non-object state, and empty requirements without mutation.

## CLI tests

- Show writes requirement Markdown exactly.
- Approve and reject produce deterministic confirmation lines.
- Workflow validation errors go to stderr and return exit code 2.

## Regression and quality

- Run the full pytest suite with configured coverage.
- Run Ruff format/check and Pyright.
- Compile against the Python 3.9 language target and build source/wheel artifacts.
- Validate all Session JSON with duplicate-key detection.
- Confirm the real PDF-export Session remains in `REQUIREMENT_REVIEW`.
