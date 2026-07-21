# Design

## Pure risk policy

Represent each candidate change with a normalized relative POSIX path and a
closed `added`, `modified`, or `deleted` kind. Sort the canonical records,
derive a SHA-256 digest, and classify the whole set by its highest risk.

High risk covers deletions and project-control/dependency files. Medium risk
covers production changes. Test, documentation, and Session evidence changes
are low risk. The result contains only paths, risk reasons, and the digest; no
source or diff text.

## Approval persistence

Store one strict versioned record at
`.agent/sessions/<active>/change-approval.json`. Creation and decisions use
same-directory optimistic atomic replacement. An existing different request,
symlink, malformed Schema, or pre-existing temporary file fails safely.

## CLI

Expose `agent approval status`, `agent approval approve`, and
`agent approval reject <reason>`. Git preparation will create the request in
the next task; the CLI only observes or decides the active request.
