# Acceptance criteria

- [ ] Only explicitly approved `DESIGN` Sessions can generate a design.
- [ ] The generator receives versioned Prompt and tracked project context.
- [ ] Structured output is validated before mutation.
- [ ] `design.md` rendering is deterministic and reviewable.
- [ ] Successful generation stops at `DESIGN_REVIEW`.
- [ ] Invalid state, approval, Session identity, context, or output fails safely.
- [ ] The generator boundary is typed, injectable, and mockable.
- [ ] Existing tests and active product Session state remain unchanged.
- [ ] No dependency or `.gitignore` update is required.
