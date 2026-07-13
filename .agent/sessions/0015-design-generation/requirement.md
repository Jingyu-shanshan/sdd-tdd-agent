# Requirement

## User request

Continue the SDD workflow with a typed design-generation core that runs only
after explicit human requirement approval.

## Functional requirements

- Load the approved active requirement plus project metadata, architecture, and
  conventions into a versioned typed request.
- Invoke an injected, mockable design generator.
- Require structured design output covering overview, decisions, components,
  data flow, interfaces, errors, security, testing, trade-offs, and questions.
- Render deterministic reviewable Markdown into `design.md`.
- Move the Session from `DESIGN` to `DESIGN_REVIEW` only after valid output.
- Reject wrong states, mismatched Session identifiers, missing approval records,
  malformed state, invalid output, and empty required context before mutation.

## Non-functional requirements

- All model interaction is typed, injectable, mockable, and testable.
- Prompt content is versioned and stored outside business logic.
- Generator output is validated before any Session artifact changes.
- Writes use Session-local atomic replacement files covered by `.gitignore`.
- No new dependency, CLI command, provider behavior, or credential handling is
  introduced in this increment.
- The active real PDF-export Session remains unchanged.

## Out of scope

- A production model adapter for design generation.
- `agent design` CLI orchestration.
- Human design approval or task breakdown.
- Automatically approving the active product requirement.
