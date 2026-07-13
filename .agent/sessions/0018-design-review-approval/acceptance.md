# Acceptance criteria

- [x] The active generated design can be displayed without mutation.
- [x] Approval records the decision and enters `TASK_BREAKDOWN`.
- [x] Rejection requires a reason, records it, and returns to `DESIGN`.
- [x] Existing state and requirement approval records are preserved.
- [x] Invalid identity, state, approval, artifact, or input fails before mutation.
- [x] CLI output and exit codes are deterministic.
- [x] Review does not invoke any model or process runner.
- [x] Existing behavior and active product Session remain unchanged.
- [x] No dependency or `.gitignore` update is required.
