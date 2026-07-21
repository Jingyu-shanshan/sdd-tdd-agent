# Requirement

## Goal

Add optional Git preparation and commit commands for one verified GREEN TDD
cycle. The commands must stage and commit only the digest-bound current test and
production artifacts after satisfying the risk approval gate.

## Acceptance criteria

- `agent git prepare` works only for an active GREEN cycle.
- Candidate paths come only from validated test/production artifact records.
- Git status is shell-free, NUL-delimited, strict, and limited to those paths.
- Preparation requests the exact risk-bound approval without touching the index.
- `agent git commit` requires approved or low-risk-exempt matching changes.
- Artifact and Git status evidence are revalidated before index/commit mutation.
- Staging and commit commands contain explicit pathspecs; `git add .` is forbidden.
- Unrelated staged/worktree changes are never included.
- A successful commit archives its approval by digest for audit and returns the
  verified commit identity without process output.
- Failures preserve recoverable approval and Session evidence.

## Out of scope

- Automatic push or remote mutation.
- Branch creation, merge, rebase, reset, or checkout.
- Enforcing Git commits for workflows that do not opt in.
