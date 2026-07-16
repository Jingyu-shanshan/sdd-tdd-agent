# Tasks

## Task 1: Final audit context

- [x] Validate review/completion/GREEN digest chain and exact state fields.
- [x] Revalidate safe final test/production artifact paths and file digests.

## Task 2: Two-gate refactor verification

- [x] Run recorded current test before recorded full suite with separate
  timeouts.
- [x] Preserve REFACTOR for failures and concurrent state/file changes.
- [x] Sanitize and bound final process evidence.

## Task 3: DONE transition and CLI

- [x] Atomically record no-source-change refactor verification and enter DONE.
- [x] Add deterministic exact `agent refactor` CLI output without a model.
- [x] Prove atomic collisions preserve REFACTOR and their ownership markers.

## Task 4: Verification and documentation

- [x] Run targeted RED/GREEN and all repository quality gates.
- [x] Run build, compile, JSON, secret, active-Session, and `.gitignore` checks.
- [x] Update architecture, README, and roadmap.
