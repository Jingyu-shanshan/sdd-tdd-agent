# Review

## Scope

The change is localized to Blind production root derivation, validation,
collection/writing, provider payloads, downstream digest verification, one
versioned Prompt, focused tests, and documentation.

## Compatibility

Non-Angular and root `src` workflows preserve Prompt v1, provider payload shape,
three-field production artifact records, and all existing path behavior. The
new root field appears only for a non-default Angular project source root.

## Safety

The writable root comes only from the current typed Angular case and strictly
parsed workspace metadata. Source collection and writing reject symlinked path
components; a sibling project path fails before mutation. The root and digest
remain bound throughout GREEN, review, and final REFACTOR verification.

## Verification

Focused RED/GREEN and full local gates pass. Hosted workflows are required
after push.
