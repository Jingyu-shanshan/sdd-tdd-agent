# Review

## Scope

The change is localized to a new read-only Angular workspace parser, design
request/proposal boundaries, one packaged Prompt, focused tests, and related
documentation. No public CLI or existing test was changed.

## Compatibility

Angular v3 activates only after verified Angular project detection and a
supported root TypeScript configuration marker. Generic and Java stay on v1;
non-Angular TypeScript stays on v2. Both request context and output records are
conditionally optional, preserving all prior payloads.

## Safety

Workspace JSON rejects duplicate keys and unsafe or inconsistent project
boundaries. Angular modules must remain under a configured source root. Typed
constraint areas, uniqueness, and all descriptive fields are validated before
any design or Session mutation.

## Verification

Focused RED/GREEN evidence and all repository quality, build, serialization,
secret, Session-preservation, and ignore audits pass. Hosted workflows are
required after push.
