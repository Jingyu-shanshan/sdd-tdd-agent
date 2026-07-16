# Tasks

## Task 1: Blind context and policy

- [x] Add digest-bound current-test source to the Blind context.
- [x] Load and validate only sanitized current RED evidence.
- [x] Collect production source while excluding every test-like path.

## Task 2: Typed source generation

- [x] Add the versioned minimal-production Prompt and typed request/result.
- [x] Add strict JSON and isolated read-only Codex adapters.
- [x] Prove model payload excludes SDD documents and future tests.

## Task 3: Safe write and state

- [x] Validate exactly one safe `src/**` production target.
- [x] Atomically create/replace with optimistic concurrency and symlink checks.
- [x] Record a digest and atomically transition RED to IMPLEMENT.

## Task 4: Continue integration and verification

- [x] Add RED dispatch and deterministic CLI output without running tests.
- [x] Run targeted RED/GREEN, all quality gates, build, and compile checks.
- [x] Check `.gitignore`, Session JSON, secrets, and active Session preservation.
- [x] Update architecture, README, and roadmap.
