# Tasks

## Task 1: Cycle evidence cleanup

- [x] Clear every stale per-cycle artifact when GREEN advances to WRITE_TEST.
- [x] Prove ordered dependency/prefix selection remains unchanged.

## Task 2: Final GREEN validation

- [x] Add typed strict GREEN evidence loading and sanitization checks.
- [x] Reuse digest-bound test and production artifact validation.
- [x] Reject missing, stale, unsafe, or concurrent final state without mutation.

## Task 3: REVIEW transition

- [x] Atomically enter REVIEW only when every generated test is complete.
- [x] Preserve audit evidence and clear only the active task pointer.
- [x] Add deterministic `agent continue` completion output without processes.

## Task 4: Verification and documentation

- [x] Run targeted RED/GREEN and all repository quality gates.
- [x] Run build, compile, JSON, secret, active-Session, and `.gitignore` checks.
- [x] Update architecture, README, and roadmap.
