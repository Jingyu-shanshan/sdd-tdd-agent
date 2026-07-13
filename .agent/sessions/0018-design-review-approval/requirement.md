# Requirement

## User request

Continue the SDD workflow with an explicit human design review gate before task
breakdown.

## Functional requirements

- Add `agent design show` to display the active generated design unchanged.
- Add `agent design approve` to record approval and move from `DESIGN_REVIEW` to
  `TASK_BREAKDOWN`.
- Add `agent design reject <reason>` to record a normalized non-empty reason and
  return to `DESIGN`.
- Preserve all existing Session state, including the approved requirement
  decision.
- Reject missing active Sessions, unsafe identifiers, mismatched state identity,
  malformed/non-object state, missing requirement approval, wrong workflow
  state, empty design, and empty rejection reason before mutation.
- Return deterministic CLI output and safe exit code 2 errors.

## Non-functional requirements

- Review is a model-free explicit human action.
- State changes use validated atomic replacement.
- Domain behavior is typed, independently testable, and separate from CLI
  dispatch.
- No dependency, credential, environment, Provider, or model behavior changes.
- The real active PDF-export Session remains unchanged.

## Out of scope

- Editing design Markdown from the CLI.
- Generating task breakdown after approval.
- Automatically approving or rejecting a design.
- Approving the current product Session.
