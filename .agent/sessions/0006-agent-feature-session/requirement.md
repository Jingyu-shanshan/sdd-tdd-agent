# Requirement: Create a feature session

## Description

Add `agent feature "<requirement>"` to create the standard SDD workspace for a
new feature and make it the project's active session.

## User story

As a developer starting a feature, I want one command to persist my request and
create the complete SDD/TDD session structure so analysis can proceed without
losing context.

## Functional requirements

- Create a unique, filesystem-safe session ID.
- Create `.agent/sessions/<session-id>/` exclusively; never merge into an
  existing session.
- Create `requirement.md`, `design.md`, `tasks.md`, `acceptance.md`,
  `test-plan.md`, `implementation.md`, `review.md`, and `state.json`.
- Persist the exact normalized user request in `requirement.md`.
- Mark generated planning artifacts as pending rather than inventing analysis,
  design, tasks, or acceptance criteria.
- Initialize state as feature kind and `ANALYSIS` workflow state.
- Update or append `current_session` in `.agent/project.yml` while preserving
  all unrelated metadata.
- `agent feature` exits 0 and reports the created session ID.
- Reject an empty or whitespace-only feature request.

## Non-functional requirements

- Use only the Python standard library at runtime.
- Session creation returns an immutable typed result.
- Generated IDs contain only letters, digits, dots, underscores, and hyphens.
- Validate externally supplied IDs before filesystem access.
- All writes are localized to the target project's `.agent` workspace.
- All `AGENTS.md` quality gates pass.

## Deferred scope

- LLM-driven requirement analysis and design generation.
- Human approval between ANALYSIS and DESIGN.
- Concurrent process locking beyond exclusive session-directory creation.
- `agent bug`, resume, rollback, and session listing.

