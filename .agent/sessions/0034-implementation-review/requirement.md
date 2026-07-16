# Requirement

## User request

Continue the complete SDD/TDD workflow with the REVIEW stage after every
planned test has trustworthy GREEN evidence.

## Requirements

- Record a digest-bound implementation-completion snapshot when entering
  REVIEW.
- Add exact `agent review` behavior for the active REVIEW Session.
- Revalidate completion snapshot, completed-test prefix, final test, artifact
  digests, and canonical GREEN evidence digest before review mutation.
- Generate deterministic `review.md` containing only audit-integrity results,
  counts, IDs, and digests; never persist source or process output.
- State explicitly that semantic automated code review remains deferred rather
  than claiming findings that were not computed.
- Atomically record a report digest and transition only REVIEW to REFACTOR.
- Invoke no model, test runner, shell command, or host mutation.
- Reject missing, malformed, stale, user-edited, symlinked, concurrently
  changed, or colliding review artifacts without state advancement.
- Keep the real active user Session and unrelated files unchanged.

## Out of scope

- Automated semantic code review or lint interpretation.
- Source-code modification or refactoring.
- Final full-suite execution and DONE transition.
- Human review comments, approvals, or remote pull-request review.
