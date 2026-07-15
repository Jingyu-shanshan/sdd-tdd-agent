# Acceptance criteria

- [x] Only approved `TEST_GENERATION` Sessions can generate a plan.
- [x] The generator receives versioned approved task/design/requirement context.
- [x] Cases have stable unique IDs and complete structured descriptions.
- [x] The first case is happy path and phases never move backward.
- [x] Dependencies reference only preceding tests.
- [x] Every approved development task has at least one planned test.
- [x] Unsafe target paths and invalid output are rejected before mutation.
- [x] Markdown rendering preserves case order and is deterministic.
- [x] Successful generation enters `IMPLEMENTATION` without writing test code.
- [x] The generator is typed, injectable, and mockable.
- [x] Existing behavior and the active product Session remain unchanged.
- [x] No dependency or unnecessary `.gitignore` update is introduced.
