# Design

## Review domain

Add `task_review.py`, parallel to the established requirement and design review
boundaries:

- `TaskReview`: immutable active Session ID, review state, and task Markdown.
- `TaskReviewDecision`: immutable decision, previous/next states, and reason.
- `_ReviewContext`: validated private Session path, state object, and artifact.
- `TaskReviewError`: safe review-specific `ValueError`.

## Validation

The loader resolves only the configured active Session, reads UTF-8 state and
`tasks.md`, requires an exact matching Session ID and `TASK_REVIEW` state, then
requires both prior approval records. Task content must be non-empty and begin
with the generated `# Task Breakdown` heading.

## State transitions

```text
TASK_REVIEW --approve--------------> TEST_GENERATION
TASK_REVIEW --reject with reason----> TASK_BREAKDOWN
```

The decision record is stored under `task_review`. A Session-local temporary
state file is atomically replaced only after complete validation.

## CLI

The existing `tasks` command family gains exact `show`, `approve`, and `reject`
subcommands. They call only the review domain and use the same deterministic
stdout and safe stderr/exit-2 contracts as earlier human gates.
