# Acceptance criteria

- [x] Only approved `TASK_BREAKDOWN` Sessions can generate tasks.
- [x] The generator receives versioned approved design/requirement context.
- [x] Tasks have stable unique IDs and required structured fields.
- [x] Dependencies reference only previously declared tasks.
- [x] Invalid output is rejected before artifact or state mutation.
- [x] Markdown rendering preserves task order and is deterministic.
- [x] Successful generation stops at `TASK_REVIEW`.
- [x] The generator is typed, injectable, and mockable.
- [x] Existing behavior and active product Session remain unchanged.
- [x] No dependency or `.gitignore` update is required.
