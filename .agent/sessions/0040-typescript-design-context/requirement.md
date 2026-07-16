# Requirement

## User request

Continue the next complete roadmap task using SDD and incremental TDD, then
commit and push it without routine approval pauses.

## Requirements

- Carry detected TypeScript package-manager, test-framework, Angular, and root
  TypeScript configuration evidence into design-generation requests when a
  supported root `tsconfig` marker exists.
- Select a dedicated versioned TypeScript design Prompt without changing the
  existing generic/Java v1 Prompt behavior.
- Add typed module design records with safe source paths, responsibilities, and
  exports.
- Add typed public API records with name, kind, signature, and owning module.
- Require at least one module for TypeScript design proposals.
- Require public APIs to reference a proposed module and reject unsafe paths,
  unsupported kinds, duplicates, and blank values.
- Render deterministic TypeScript module and public API sections in SDD design
  artifacts.
- Extend JSON and Codex design schemas without breaking providers that return
  the existing generic fields for non-TypeScript projects.
- Keep model interaction typed, injectable, mockable, and versioned.
- Preserve v1 compatibility when that explicit configuration evidence is
  absent, preserve the active user Session, and inspect `.gitignore`
  requirements.

## Out of scope

- Parsing the full TypeScript compiler configuration graph.
- Inferring existing source exports through a TypeScript AST dependency.
- Angular-specific component/service test planning; that remains a later task.
- Changing existing Java design artifacts or public CLI commands.
