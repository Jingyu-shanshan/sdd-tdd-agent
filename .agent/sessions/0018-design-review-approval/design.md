# Design

## Review boundary

`design_review` owns loading and validating the active design review context and
applying explicit human decisions. Immutable `DesignReview` and
`DesignReviewDecision` results keep CLI rendering independent of state mutation.

## State transitions

```text
DESIGN_REVIEW --approve--------> TASK_BREAKDOWN
DESIGN_REVIEW --reject(reason)-> DESIGN
```

Both decisions write a `design_review` object. Approval records only
`{"decision": "approved"}`. Rejection also records the normalized human reason.
All unrelated state keys and the `requirement_review` record are preserved.

## Validation and writes

- Resolve the active Session through validated project status.
- Require a JSON object with matching `session_id` and exact DESIGN_REVIEW state.
- Require `requirement_review.decision == approved`.
- Require non-empty generated Markdown beginning with `# Design Proposal`.
- Require a non-empty rejection reason before context loading or mutation.
- Write the complete state through a Session-local `.tmp` file and atomic
  replacement.

## CLI

- `agent design show` writes the design artifact unchanged.
- `agent design approve` reports `TASK_BREAKDOWN`.
- `agent design reject <reason>` reports `DESIGN`.
- Safe domain errors go to stderr with exit code 2.
