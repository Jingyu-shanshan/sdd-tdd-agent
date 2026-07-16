# Tasks

## Task 1: Full-suite planning and configuration

- [x] Add typed full-suite commands for every supported ecosystem.
- [x] Add strict explicit full-suite timeout configuration.
- [x] Prove commands contain no current-test filter or shell string.

## Task 2: Artifact-safe verification

- [x] Validate current test and production digests around both processes.
- [x] Run current test first and full suite only after a pass.
- [x] Preserve IMPLEMENT for process/configuration/concurrency failures.

## Task 3: Recovery and GREEN evidence

- [x] Return trustworthy current-test and regression failures to RED.
- [x] Persist only sanitized bounded retry/GREEN evidence atomically.
- [x] Append only the current test to the validated completed prefix.

## Task 4: Continue integration and verification

- [x] Dispatch IMPLEMENT without invoking the model and render CLI output.
- [x] Run targeted RED/GREEN, full quality gates, build, and compile checks.
- [x] Check `.gitignore`, Session JSON, secrets, and active Session preservation.
- [x] Update README, architecture, and roadmap.
