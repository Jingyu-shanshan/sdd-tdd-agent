# Requirement

## User request

Continue through the remaining roadmap using SDD and incremental TDD, with one
commit and push for each complete task.

## Requirements

- Extend Blind production-source generation from the legacy `src/**` boundary
  to the configured source root of the Angular project that owns the current
  test.
- Support Angular monorepo application and library roots such as
  `projects/shared/src/**` without allowing writes to sibling projects.
- Supply only the normalized writable source-root boundary to the Blind model;
  do not expose `angular.json`, SDD artifacts, future tests, or Session state.
- Collect, validate, write, digest-check, and finally verify production sources
  under the same exact boundary.
- Keep non-Angular and root-Angular projects restricted to `src/**` with their
  existing Prompt and provider payload compatibility.
- Reject unsafe, test-like, hidden, unsupported, out-of-root, and symlinked
  paths before project mutation.
- Preserve the active user Session and audit `.gitignore` requirements.

## Out of scope

- Writing more than one production file per TDD cycle.
- Allowing a test to modify multiple Angular projects.
- Inferring source roots from directory layout or source imports.
- Changing test-generation or Angular workspace semantics.

