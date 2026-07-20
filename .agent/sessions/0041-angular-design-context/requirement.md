# Requirement

## User request

Continue the next complete roadmap task using SDD and incremental TDD, then
commit and push it without routine approval pauses.

## Requirements

- Load verified Angular workspace version and project boundaries from the root
  `angular.json` only for detected Angular projects.
- Represent each application or library with its configured name, project type,
  root, source root, and optional prefix.
- Allow proposed TypeScript modules only within one configured Angular project
  source root, including monorepo library paths.
- Reject malformed JSON, duplicate keys, unsupported project types, duplicate
  project names, unsafe paths, and inconsistent root/source-root boundaries.
- Select a dedicated packaged and versioned Angular design Prompt while keeping
  generic, Java, and non-Angular TypeScript Prompt behavior unchanged.
- Add typed Angular architecture constraints with area, decision, rationale,
  and verification fields.
- Require at least one valid Angular constraint for Angular design proposals,
  reject unsupported/duplicate areas, and reject Angular records in other
  project types.
- Exchange Angular context and proposal records through strict provider-neutral
  and Codex JSON Schemas.
- Render deterministic Angular workspace and architecture-constraint sections
  in the SDD design artifact.
- Preserve the active user Session and audit `.gitignore` requirements.

## Out of scope

- Resolving Angular builders, targets, configurations, or inherited files.
- Inferring standalone components, signals, zones, or runtime behavior from
  source code.
- Generating Angular-specific test plans or source code; those remain later
  roadmap tasks.
- Changing public CLI commands or existing Java/TypeScript v1/v2 behavior.
