# Design

## Review boundary

`requirement_review` owns loading the active review context, validating the
Session, rendering no content of its own, and applying explicit decisions.
Immutable result models expose the active requirement and completed decision to
the CLI.

## State transitions

```text
REQUIREMENT_REVIEW --approve--------> DESIGN
REQUIREMENT_REVIEW --reject(reason)-> ANALYSIS
```

Both transitions add a `requirement_review` object to `state.json`. Approval
records `{"decision": "approved"}`. Rejection also records the normalized
human reason. Existing Session state keys are preserved.

## Validation and filesystem policy

- Resolve the active Session through tracked project metadata.
- Reuse the existing project-status identifier validation before resolving a
  Session path.
- Require a JSON object whose `session_id` matches the selected Session and
  whose state is exactly `REQUIREMENT_REVIEW`.
- Require non-empty requirement Markdown and a non-empty rejection reason.
- Serialize the complete validated state and replace `state.json` atomically
  through a Session-local ignored temporary file.
- A show operation is read-only; a failed decision leaves the current state
  untouched.

## CLI contract

- `agent requirement show` writes the stored Markdown unchanged.
- `agent requirement approve` reports the Session identifier and `DESIGN`.
- `agent requirement reject <reason>` reports the Session identifier and
  `ANALYSIS`.
- Invalid use or workflow data writes a sanitized `Error:` message to stderr
  and returns exit code 2.
