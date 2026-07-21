# Implementation

## Cycle 1: Angular monorepo contract (RED)

Seven focused tests initially failed because the collector accepted only its
legacy root argument and the request had no typed writable-root metadata.

## Cycle 2: Typed root boundary (GREEN)

Added strict current-case project resolution, a versioned Angular Blind Prompt,
conditional provider payload roots, and parameterized source validation,
collection, and atomic writing. Generic v1 requests retain their exact payload
and `src/**` behavior.

## Cycle 3: Audit-chain integration (GREEN)

Non-default Angular artifacts now bind `source_root`. GREEN validation and final
REFACTOR verification use the bound root plus digest. A focused end-to-end test
proves an Angular library can progress from RED through DONE, while a tampered
sibling root is rejected.

## Cycle 4: Verification

All 735 tests pass with 93.78% coverage. Ruff, Pyright, formatting, build,
compile, Schema, secret, active-Session, and ignore audits are required before
commit. Existing ignore rules cover all generated artifacts, so `.gitignore`
does not need a change.
