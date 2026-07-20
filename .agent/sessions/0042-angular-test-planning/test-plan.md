# Test Plan

## RED

- Prove Angular test requests still use generic v1 with no workspace context.
- Prove typed Angular per-case metadata and adapter fields do not exist.
- Prove Angular plans incorrectly accept generic cases and out-of-bound paths.
- Prove rendered Angular metadata cannot survive TDD-cycle parsing.

## GREEN

- Add conditional workspace context and a packaged v2 Angular Prompt.
- Add typed optional case fields, strict Schema decoding, and contextual
  validation.
- Extend deterministic rendering/parser contracts without changing legacy
  Markdown.
- Re-run focused Angular, generic test-plan, and TDD-cycle suites.

## Regression

- Run Ruff lint and formatting, Pyright, and full pytest coverage.
- Build the distribution and compile production modules.
- Validate Agent JSON and test-plan Schema serialization.
- Scan for secrets, preserve the active Session, and audit ignored files.
- Push and require standard and real-toolchain GitHub workflows to pass.
