# Requirement

## User request

Continue the SDD workflow by generating a structured, reviewable task breakdown
from explicitly approved requirements and design.

## Functional requirements

- Load the approved requirement, approved generated design, versioned Prompt,
  project metadata, architecture, and conventions into a typed request.
- Invoke an injected, mockable task-breakdown generator.
- Represent ordered tasks with stable ID, title, objective, affected areas,
  dependencies, acceptance criteria, and test targets.
- Require dependencies to reference only previously declared task IDs.
- Reject duplicate/unsafe IDs, unknown or forward dependencies, empty required
  fields, blank tuple items, and invalid generator result types.
- Render deterministic Markdown into `tasks.md`.
- Move from `TASK_BREAKDOWN` to `TASK_REVIEW` only after complete validation.
- Preserve existing Session decisions and state keys.

## Non-functional requirements

- All model interaction is typed, injectable, mockable, and testable.
- Prompt content is versioned and stored outside business logic.
- State, approval, context, and generated output are validated before mutation.
- Artifact/state replacement uses Session-local atomic writes.
- No dependency, CLI command, Provider adapter, or credential behavior changes.
- The active real PDF-export Session remains unchanged.

## Out of scope

- Production JSON/Codex adapters for task breakdown.
- `agent tasks` CLI orchestration.
- Human task approval/rejection.
- Test generation or implementation execution.
