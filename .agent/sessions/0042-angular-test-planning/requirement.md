# Requirement

## User request

Continue the next complete roadmap task using SDD and incremental TDD, then
commit and push it without routine approval pauses.

## Requirements

- Detect verified Angular projects during test-plan generation and load their
  strict workspace application/library boundaries.
- Select a dedicated packaged and versioned Angular test-generation Prompt
  without changing generic, Java, or non-Angular TypeScript v1 behavior.
- Add typed per-case Angular metadata for the owning project, subject kind,
  configured testing facilities, template contracts, dependency-injection
  behavior, and asynchronous behavior.
- Support component, service, directive, pipe, routing, form, and HTTP test
  subjects without requiring irrelevant categories in every feature.
- Require every Angular case to carry valid Angular metadata and an exact
  `.spec.ts` file within its configured project source root.
- Reject unsupported subject kinds, unknown projects, unsafe/out-of-bound test
  paths, empty facilities, invalid contract values, and Angular records in
  non-Angular workflows before artifact mutation.
- Extend provider-neutral and Codex JSON Schemas compatibly and strictly.
- Render Angular details deterministically and parse them back without loss when
  selecting the next one-test-at-a-time TDD cycle.
- Preserve the active user Session and audit `.gitignore` requirements.

## Out of scope

- Generating executable Angular test source; the existing isolated test-source
  stage remains responsible for code generation.
- Expanding Blind production writes to Angular monorepo library source roots.
- Inferring installed testing libraries or runtime conventions from source.
- Requiring all seven subject categories when a requirement uses only a subset.
- Changing public CLI commands or existing test execution commands.
