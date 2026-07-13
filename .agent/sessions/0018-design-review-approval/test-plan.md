# Test plan

## Unit tests

- Load the active design artifact and immutable review context.
- Approve into TASK_BREAKDOWN while preserving all state keys.
- Reject into DESIGN with a normalized reason.
- Reject wrong state, mismatched Session identity, non-object JSON, missing
  requirement approval, empty design, empty reason, and no active Session.
- Assert invalid decisions leave state unchanged.

## CLI tests

- Show writes exact Markdown.
- Approve and reject produce deterministic success lines.
- Empty rejection reason produces safe stderr and exit code 2.

## Quality

- Run full pytest with coverage, Ruff format/check, and Pyright.
- Compile and build source/wheel packages.
- Validate all Session JSON without duplicate keys.
- Review `.gitignore` and preserve the active PDF Session.
