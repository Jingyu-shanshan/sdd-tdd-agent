# Test Plan

## RED

- Prove a valid pnpm/Vitest TypeScript project still receives generic v1 design
  context and no typed TypeScript context.
- Prove generic proposals are incorrectly accepted for a TypeScript workflow.
- Prove typed module/API proposal records and adapter fields do not yet exist.

## GREEN

- Add typed records and conditional request loading with no generic behavior
  changes.
- Preserve v1 design behavior for metadata-only TypeScript fixtures without a
  supported root `tsconfig` marker.
- Add optional Schema fields, strict decoding, validation, and rendering.
- Re-run all focused TypeScript tests and existing design tests.

## Regression

- Run Ruff lint and formatting, Pyright, and full pytest coverage.
- Build the distribution and compile production modules.
- Validate Agent JSON and Codex output Schema serialization.
- Scan for secrets, preserve the active Session, and audit ignored files.
- Push and require standard and toolchain GitHub workflows to pass.
