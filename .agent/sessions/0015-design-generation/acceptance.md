# Acceptance criteria

- [x] Only explicitly approved `DESIGN` Sessions can generate a design.
- [x] The generator receives versioned Prompt and tracked project context.
- [x] Structured output is validated before mutation.
- [x] `design.md` rendering is deterministic and reviewable.
- [x] Successful generation stops at `DESIGN_REVIEW`.
- [x] Invalid state, approval, Session identity, context, or output fails safely.
- [x] The generator boundary is typed, injectable, and mockable.
- [x] Existing tests and active product Session state remain unchanged.
- [x] No dependency or `.gitignore` update is required.
