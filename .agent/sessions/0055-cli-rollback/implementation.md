# Implementation

## Cycle 1

### RED

The focused test module failed at import because
`rollback_active_green_cycle` did not exist.

### GREEN

The existing GREEN context and injected Git runner now validate clean exact
paths, a matching single-parent Agent HEAD, and its exact path set. Native
`git restore` restores only those worktree paths, followed by an optimistic
atomic `GREEN` to `WRITE_TEST` state update. A failed state update restores the
paths from HEAD.

The CLI routes `agent rollback` through the same injected runner and emits only
Session/test identity. Focused rollback, Git integration, and manifest
regression tests pass without changing the read-only IDE manifest contract.

## Verification

All 886 tests pass at 92.12% coverage. Ruff format/check, Pyright, source and
wheel builds, module compilation, Session duplicate-key/active-state checks,
secret and whitespace scans, and CLI failure-path checks pass. The existing
`.agent/**/*.tmp` ignore rule already covers the rollback atomic state file.
