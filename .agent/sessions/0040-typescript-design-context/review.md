# Review

## Scope

The change is localized to design request loading, the design adapter, one
versioned Prompt, focused tests, and related documentation. Existing CLI and
generic/Java design contracts remain unchanged.

## Compatibility

TypeScript v2 activates only when verified Node project detection and a
supported root `tsconfig` marker are both present. Metadata-only TypeScript,
generic, and Java projects preserve the exact v1 request shape. Optional JSON
fields preserve legacy provider responses outside the typed workflow.

## Safety

Typed proposals are validated before Session or design mutation. Module paths
are constrained to normalized TypeScript source paths, exports are non-empty,
API kinds are closed, and module/API references and identities are checked.

## Verification

Focused RED/GREEN evidence and all repository quality, build, serialization,
secret, Session-preservation, and ignore audits pass. Hosted workflows are
required after push.
