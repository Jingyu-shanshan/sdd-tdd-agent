# Tasks

## Task 1: Completion snapshot

- [x] Bind REVIEW entry to exact completed tests, final test, evidence, and
  artifact digests.
- [x] Prove snapshot tampering is detectable.

## Task 2: Deterministic review report

- [x] Validate the active REVIEW state and completion snapshot strictly.
- [x] Render bounded source/output-free `review.md` with explicit scope.
- [x] Reject missing, edited, unsafe, or symlinked review artifacts.

## Task 3: Atomic REFACTOR transition

- [x] Record report/completion digests and enter only REFACTOR.
- [x] Add exact `agent review` CLI output with no external calls.
- [x] Preserve REVIEW on concurrency, filesystem, and temporary collisions.

## Task 4: Verification and documentation

- [x] Run targeted RED/GREEN and all repository quality gates.
- [x] Run build, compile, JSON, secret, active-Session, and `.gitignore` checks.
- [x] Update architecture, README, and roadmap.
