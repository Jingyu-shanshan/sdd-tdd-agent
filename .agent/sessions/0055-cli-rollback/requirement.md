# Requirement

## Goal

Add the original design's public `agent rollback` command without introducing
arbitrary history rewriting or a second backup system.

## Requirements

- Roll back only the active Session's current verified GREEN cycle.
- Require the matching Agent GREEN commit to be the current Git HEAD.
- Restore only that cycle's exact test and production paths from HEAD's single
  parent, using shell-free bounded Git commands.
- Preserve unrelated staged, tracked, and untracked work.
- Return the cycle to `WRITE_TEST`, remove its completed marker and stale
  artifacts/evidence, and allow the normal incremental TDD loop to retry it.
- Reject dirty target paths, mismatched commits, merge/root commits, malformed
  Git output, concurrent Session changes, and atomic-write collisions.
- Keep Git history unchanged and never accept a user-supplied revision.

## Non-goals

- Rolling back arbitrary commits or completed/older cycles.
- Reverting requirement, design, task, or test-plan approvals.
- Creating a backup database or new dependency.
