# Requirement

## Goal

Add a deterministic human approval gate for Git-bound project changes. The
gate must classify an exact change set, bind the decision to its digest, and
fail safely if the project changes before the decision is consumed.

## Acceptance criteria

- Relative changed paths and change kinds are strictly validated.
- Documentation/test-only changes are low risk; production changes are medium
  risk; deletions and control/dependency files are high risk.
- Medium/high risk changes require explicit human approval; low risk records
  that approval is not required.
- One active Session owns one bounded approval record for `git_commit`.
- Approval/rejection decisions are atomic, deterministic, and digest-bound.
- Existing or tampered approval records are never silently replaced.
- CLI status/approve/reject commands expose no source or diff content.

## Out of scope

- Running Git or mutating the index.
- Interactive prompts or terminal UI.
- User-configurable risk policy.
