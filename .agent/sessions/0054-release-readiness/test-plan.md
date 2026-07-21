# Test plan

## Existing automated contracts

- Run all 877 repository tests with the configured 80% coverage floor.
- Run Ruff check/format and Pyright against production and test code.
- Build both source and wheel distributions.

## Repository integrity

- Parse every Session state with duplicate-key rejection.
- Verify the active user Session remains exactly unchanged.
- Compile production modules and scan tracked content for secret-like material.
- Confirm ignored runtime/cache/build artifacts stay ignored and no required
  tracked source is accidentally excluded.
- Require a clean whitespace diff and review every changed path.

## Hosted evidence

- Push the single release-readiness commit.
- Require both GitHub CI and real-toolchain workflows to finish successfully.
