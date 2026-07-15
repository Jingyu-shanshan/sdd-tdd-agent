# Acceptance criteria

- [x] Generated cases parse and retain exact order/content.
- [x] Only the first incomplete dependency-ready case is selected.
- [x] Cycle start records current task/test and increments the cycle atomically.
- [x] An active non-GREEN cycle cannot be overwritten.
- [x] Invalid state/progress/artifacts fail before mutation.
- [x] Blind context contains no requirement, design, tasks, or future tests.
- [x] No dependency or `.gitignore` update is introduced.
