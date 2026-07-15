# Requirement

## User request

Continue the SDD workflow by adding the typed core that generates an ordered,
reviewable incremental test plan from approved requirements, design, and tasks.

## Functional requirements

- Accept only `TEST_GENERATION` Sessions with persisted approved requirement,
  design, and task decisions.
- Load the generated requirement, design, tasks, versioned Prompt, project
  metadata, architecture, and conventions into a typed request.
- Invoke an injected, mockable test-plan generator.
- Represent each planned test with stable test/task IDs, phase, title, objective,
  target file/name, preconditions, action, expected outcomes, and dependencies.
- Enforce phase order: happy path, boundary, exception, integration, regression.
- Require the first planned test to be happy path.
- Require test dependencies to reference only preceding test IDs.
- Require every approved development task to have at least one planned test.
- Reject unsafe test identifiers and absolute/traversing test-file paths.
- Render deterministic Markdown into `test-plan.md`.
- Move to `IMPLEMENTATION` only after complete plan validation.

## Non-functional requirements

- All model interaction is typed, injectable, mockable, and testable.
- Prompt content is versioned and stored outside business logic.
- State, approvals, context, and generated output are validated before mutation.
- Artifact/state replacement uses Session-local atomic writes.
- Generate plans only; do not write or run test code.
- Add no dependency, CLI, Provider adapter, credential, or environment behavior.
- Preserve the active PDF-export Session unchanged.

## Out of scope

- JSON/Codex test-plan adapters.
- `agent tests` CLI orchestration.
- Test source generation and RED execution.
- Production implementation, refactoring, or review.
