# Requirement

## User request

Continue the SDD workflow by adding a mandatory human review gate for generated
task breakdowns.

## Functional requirements

- Load and show the active generated `tasks.md` only in `TASK_REVIEW`.
- Require persisted approved requirement and design decisions.
- Validate active Session identity, JSON object state, generated task heading,
  non-empty task content, and required review files before any decision.
- Approve tasks by recording `task_review.decision=approved` and entering
  `TEST_GENERATION`.
- Reject tasks only with a non-empty normalized reason, record the decision and
  reason, and return to `TASK_BREAKDOWN`.
- Preserve all unrelated Session state fields.
- Write review decisions through a Session-local atomic replacement.
- Add `agent tasks show`, `agent tasks approve`, and `agent tasks reject <reason>`.

## Non-functional requirements

- Review operations are deterministic and invoke no model or process runner.
- Invalid states, artifacts, reasons, or filesystem data fail before mutation.
- Errors are safe and CLI failures use stderr plus exit code 2.
- Add no dependency, Provider, credential, environment, or configuration change.
- Preserve the active PDF-export Session unchanged.

## Out of scope

- Test generation implementation.
- Automatic execution after approval.
- Editing generated task content during review.
- New Provider or installation behavior.
