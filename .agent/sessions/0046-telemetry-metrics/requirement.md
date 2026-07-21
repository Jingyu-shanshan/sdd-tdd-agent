# Requirement

## Goal

Record privacy-safe model/test execution telemetry and expose deterministic
per-Session metrics without changing Provider or test-runner behavior.

## Acceptance criteria

- All model and test runner calls made by workflow CLI commands are observed.
- Events contain operation, kind, sanitized tool identity, success/return code,
  duration, Prompt version/digest when present, and typed usage/cost fields.
- Prompt/source/review text, command arguments, stdout, stderr, credentials, and
  personal data are never persisted.
- Unsupported token/cost usage is recorded as unavailable, never estimated.
- Metrics are append-only below `.agent/metrics` with strict read validation.
- `agent metrics` renders active-Session call counts, rates, duration, and usage.
- Injected runners and clocks keep telemetry fully testable.

## Out of scope

- Provider-specific token/billing extraction without a verified CLI contract.
- Failure-memory recommendations; implemented in the next task.
- Remote telemetry export.
