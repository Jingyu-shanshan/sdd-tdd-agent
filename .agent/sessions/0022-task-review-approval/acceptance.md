# Acceptance criteria

- [x] Only the active `TASK_REVIEW` Session can be reviewed.
- [x] Both requirement and design approvals are mandatory.
- [x] Show returns generated non-empty task Markdown without mutation.
- [x] Approval records the decision and enters `TEST_GENERATION`.
- [x] Rejection requires and normalizes a reason, then enters `TASK_BREAKDOWN`.
- [x] Existing Session fields and prior approvals are preserved.
- [x] Invalid inputs and artifacts fail before state mutation.
- [x] Review commands invoke no model or process runner.
- [x] CLI success and safe failure output is deterministic.
- [x] Existing behavior and the active product Session remain unchanged.
- [x] No dependency or unnecessary `.gitignore` update is introduced.
