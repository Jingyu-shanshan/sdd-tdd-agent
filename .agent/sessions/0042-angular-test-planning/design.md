# Design

## Request context

Test-request loading reuses verified project detection. Angular profiles load
the strict `AngularWorkspace` and select `prompts/test_generation/v2-angular.md`.
Other project types retain the exact v1 request shape.

## Typed case extension

Add immutable `AngularTestCasePlan` with:

- `project`
- `subject_kind`
- `test_facilities`
- `template_contracts`
- `dependency_injection`
- `async_behavior`

Append optional `angular` to `TestCasePlan`. The JSON case Schema exposes this
strict nested object as optional for compatibility. Angular workflows require
it on every case; non-Angular workflows reject it.

## Validation

Subject kinds use a closed seven-value vocabulary. Project names must reference
the verified workspace. Test files must be normalized relative `.spec.ts`
paths below that project's configured `sourceRoot`. Testing facilities are
required non-empty strings; the three explicit behavior collections may be
empty but must contain only non-empty strings when supplied.

The existing happy/boundary/exception/integration/regression ordering, task
coverage, stable IDs, and preceding dependency rules remain authoritative.

## Rendering and parsing

Angular cases append six fixed Markdown sections after the existing sections.
The TDD parser accepts either the exact legacy section set or the exact extended
Angular set, reconstructs typed metadata, and then reuses domain validation.
This preserves metadata when `agent continue` selects exactly one current test.

## Compatibility

Request payloads include `angular_context` only when present. Legacy case JSON,
Markdown, dataclass construction, and provider output remain valid outside an
Angular workflow. The shared Schema keeps original required fields unchanged.
