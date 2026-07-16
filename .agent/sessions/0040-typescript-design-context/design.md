# Design

## Context selection

At design-request load time, reuse `detect_project`. When it returns a
TypeScript profile with at least one supported root `tsconfig` marker, create
an immutable `TypeScriptProjectContext` containing the package manager, one
verified test framework, Angular classification, and the sorted markers.
Projects without this explicit evidence, plus generic and Java projects,
retain the existing request shape and v1 Prompt.

TypeScript requests use `prompts/design_generation/v2-typescript.md`. Prompt
selection is deterministic and stored in the typed request.

## Typed proposal extension

Extend `DesignProposal` with default-empty tuples so existing constructors and
provider responses remain compatible:

- `TypeScriptModuleDesign(path, responsibility, exports)`
- `TypeScriptPublicApiDesign(name, kind, signature, module)`

The JSON output Schema exposes both arrays as optional. A TypeScript workflow,
however, requires at least one module during domain validation. Non-TypeScript
workflows reject unexpected TypeScript records.

## Validation

Module paths must be normalized relative `src/**/*.ts` or `src/**/*.tsx` paths
without traversal. Paths and API identities must be unique. Text fields and
exports must be non-empty. API kinds use a closed set supporting TypeScript and
future Angular design vocabulary. Every API module must reference a proposed
module path.

## Rendering

Generic sections retain their existing order and content. TypeScript requests
append deterministic project-context, module, and public-API sections. Empty
public APIs render explicitly rather than disappearing.

## Compatibility

Request payloads include `typescript_context` only when present, preserving the
exact legacy provider-neutral payload for non-TypeScript requests. The decoder
requires all original fields, permits the two known optional fields, and still
rejects unknown keys.
