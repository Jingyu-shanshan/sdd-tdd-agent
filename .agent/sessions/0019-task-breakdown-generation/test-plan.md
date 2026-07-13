# Test plan

## Request and rendering

- Load Prompt version/content, approved requirement/design, and tracked context.
- Render summary, ordered tasks, task fields, risks, and questions in stable order.
- Render empty optional lists explicitly.

## Task validation

- Accept a valid two-task chain.
- Reject wrong return type, empty summary/tasks, duplicate or unsafe IDs, forward
  or unknown dependencies, empty acceptance criteria, empty test targets, and
  blank tuple members.
- Verify every invalid result leaves tasks/state byte-for-byte unchanged.

## State validation

- Reject wrong state, mismatched Session ID, non-object state, missing
  requirement approval, and missing design approval before generator execution.

## Quality

- Run full pytest with coverage, Ruff format/check, and Pyright.
- Compile and build source/wheel packages and verify Prompt packaging.
- Validate all Session JSON without duplicate keys.
- Review `.gitignore` and preserve the active PDF Session.
