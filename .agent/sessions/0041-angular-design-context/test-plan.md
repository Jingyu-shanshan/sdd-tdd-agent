# Test Plan

## RED

- Prove no strict Angular workspace loader or typed records exist.
- Prove detected Angular designs still use the TypeScript Prompt and lack
  workspace context.
- Prove generic typed proposals are incorrectly accepted for Angular workflows.
- Prove adapter context, typed constraints, and deterministic sections do not
  exist.

## GREEN

- Add strict immutable workspace parsing with explicit boundary failures.
- Add conditional v3 Prompt/context selection without changing other projects.
- Add optional strict Schema fields, decoding, semantic validation, and
  rendering.
- Re-run focused Angular tests and all existing design tests.

## Regression

- Run Ruff lint and formatting, Pyright, and full pytest coverage.
- Build the distribution and compile production modules.
- Validate Agent JSON and design Schema serialization.
- Scan for secrets, preserve the active Session, and audit ignored files.
- Push and require standard and real-toolchain GitHub workflows to pass.
