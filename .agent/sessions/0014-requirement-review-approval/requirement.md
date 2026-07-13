# Requirement

## User request

Continue the core SDD workflow by implementing the explicit human requirement
review gate that follows requirement analysis.

## Functional requirements

- Add `agent requirement show` to display the active analyzed requirement.
- Add `agent requirement approve` to move an active Session from
  `REQUIREMENT_REVIEW` to `DESIGN`.
- Add `agent requirement reject <reason>` to record a non-empty reason and move
  the Session back to `ANALYSIS`.
- Record each decision in Session state without discarding existing state data.
- Reject missing active Sessions, unsafe identifiers, mismatched Session data,
  malformed state, and invalid workflow states.
- Return deterministic CLI output and exit code 2 for safe user-facing errors.

## Non-functional requirements

- Review is an explicit human action and never invokes an LLM.
- Validate all input and current state before an atomic state replacement.
- Keep review behavior typed, independently testable, and separate from CLI
  dispatch.
- Preserve the current real product Session during implementation verification.
- Use only the Python standard library and existing dependencies.

## Out of scope

- Editing requirement Markdown from the CLI.
- Automatically answering open questions.
- Generating the design after approval.
- Approving or rejecting the current real PDF-export Session.
