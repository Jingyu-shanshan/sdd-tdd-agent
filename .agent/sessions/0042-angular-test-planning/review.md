# Review

## Scope

The change is localized to test-plan request/model/adapter behavior, the
deterministic TDD parser, one packaged Prompt, focused tests, and related
documentation. It does not write test or production source and changes no CLI.

## Compatibility

Angular v2 activates only for verified Angular project metadata. Generic, Java,
and other TypeScript workflows retain v1 request payloads, JSON cases,
dataclass construction, Markdown sections, and parser behavior. The new nested
Schema field is optional but semantically mandatory only in Angular workflows.

## Safety

Every Angular case references a configured project, supported subject, and
exact `.spec.ts` path under that project's source root. Facilities are
non-empty, explicit template/DI/async collections are validated, and all
metadata survives rendering and contextual parser validation before a TDD cycle
selects one current test.

## Verification

Focused RED/GREEN evidence and all repository quality, build, serialization,
secret, Session-preservation, and ignore audits pass. Hosted workflows are
required after push.
