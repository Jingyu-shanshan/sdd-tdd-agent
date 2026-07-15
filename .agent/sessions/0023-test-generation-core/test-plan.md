# Test plan

## Request and rendering

- Load Prompt version/content, approved requirement/design/tasks, and tracked
  project context.
- Render ordered cases, task/phase/target, descriptions, dependencies, risks,
  and questions deterministically.
- Render empty optional lists explicitly.

## Plan validation

- Accept a valid two-task, two-case incremental plan.
- Reject wrong result type, empty summary/cases, invalid/duplicate IDs, unknown
  tasks, missing task coverage, non-happy first case, backward phases,
  forward/unknown dependencies, empty required outcomes, and unsafe paths.
- Verify every invalid result leaves plan/state byte-for-byte unchanged.

## State validation

- Reject wrong state, mismatched Session ID, non-object state, and each missing
  approval before generator execution.

## Quality

- Run full pytest with coverage, Ruff format/check, and Pyright.
- Compile and build source/wheel packages and verify Prompt packaging.
- Validate all Session JSON without duplicate keys.
- Review `.gitignore` and preserve the active PDF Session.
