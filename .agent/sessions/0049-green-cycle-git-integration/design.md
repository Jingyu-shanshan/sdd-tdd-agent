# Design

## Git tool boundary

Define an injected typed runner with tokenized commands, explicit project cwd,
finite timeout, captured result, and a production `shell=False` implementation.
Errors expose only safe fixed messages.

## Preparation

Reuse existing GREEN artifact validators for the exact test and production
paths/digests. Run scoped `git status --porcelain=v1 -z` and decode a closed
added/modified/deleted set. Feed only that set to the change-risk assessor and
persist the approval request. Do not run `git add` or `git commit`.

## Commit

Reload artifacts, status, and approval and require the same digest. Run exact
`git add -- <paths>`, verify the cached names, revalidate artifact/status input,
then run `git commit --only -m <generated> -- <paths>`. Verify HEAD with
`git rev-parse --verify HEAD` and archive the approval record by digest.

The commands intentionally remain opt-in so existing workflow compatibility is
preserved while each GREEN cycle can be committed before advancing.
