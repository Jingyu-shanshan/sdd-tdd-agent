# Test Plan

## RED

- A REVIEW Session cannot yet create an isolated typed semantic request.
- Typed approved findings cannot be rendered, persisted, or finalized.
- Required changes cannot block the REFACTOR transition.
- Strict provider payload/Schema and CLI orchestration do not exist.

## GREEN

- Add core request/result models, validation, deterministic report writing, and
  optimistic atomic state mutation.
- Add provider-neutral and Codex adapters plus active command composition.
- Extend invariant finalization only when a valid approved semantic record is
  present; retain legacy fallback.

## Regression

- Run Ruff lint/format, Pyright, full pytest coverage, build, compile, Schema,
  secret, active-Session, and ignored-file audits.
- Push and require both hosted workflows to pass.
