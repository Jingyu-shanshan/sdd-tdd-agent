# Requirement

## User request

Continue all roadmap tasks with SDD and incremental TDD, committing and pushing
each complete task without routine approval pauses.

## Requirements

- Add an explicit automated semantic code-review step inside REVIEW.
- Review Clean Code, SOLID, duplication, complexity, readability, potential
  bugs, performance, and security through a closed typed vocabulary.
- Use a packaged versioned Prompt and a mockable, dependency-injected reviewer
  with strict provider-neutral JSON and isolated Codex adapters.
- Supply only the digest-bound final test and production source plus completion
  identity; never expose requirements, design, tasks, process output, raw state,
  credentials, or unrestricted project access.
- Validate finding IDs, areas, severity, exact visible file paths, line numbers,
  messages, recommendations, decision consistency, size, and uniqueness before
  mutation.
- Store a deterministic source-free report and digest while remaining in
  REVIEW. Only the existing deterministic integrity step may enter REFACTOR.
- Preserve the legacy invariant-only `agent review` flow when semantic review
  has not been requested.
- Preserve the active user Session and audit `.gitignore` requirements.

## Out of scope

- Modifying source code during review.
- Automatically accepting a review that reports required changes.
- Behavior-preserving source refactoring; that is the next roadmap task.
- Multi-file or repository-wide semantic analysis.
