# Design

## Review context

Reuse the existing completion/integrity validation, then independently verify
the final test and production file digests. Build an immutable request with the
v1 semantic Prompt, completion digest, final test ID, and exactly two bounded
source snapshots.

## Typed result

`GeneratedSemanticReview` contains a summary, ordered immutable findings, and
an `approved` or `changes_required` decision. Each finding has a stable ID,
closed review area, `info`/`warning`/`error` severity, one visible path, a valid
line number, a non-empty message, and a non-empty recommendation.

Decision semantics are deterministic: any error requires changes; approval may
contain informational or warning observations but no error. Duplicate IDs and
duplicate finding locations are rejected.

## Mutation and transition

Write deterministic `review.md` and a digest-bound `semantic_review` state
record atomically after revalidating state, files, and the pending report. Keep
the Session in REVIEW. The existing `agent review` integrity command recognizes
an approved semantic record, preserves its report, and enters REFACTOR with a
`semantic_review_passed` audit decision. Required changes remain in REVIEW.

## Adapters

JSON-command and Codex adapters share an exact nested Schema. Codex runs in a
project-external ephemeral read-only exchange and receives only the typed
payload. Provider errors never include request/source content.
