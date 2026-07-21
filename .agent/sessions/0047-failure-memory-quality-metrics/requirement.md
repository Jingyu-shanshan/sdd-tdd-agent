# Requirement

## Goal

Turn privacy-safe telemetry into durable cross-Session failure memory and
deterministic task/test quality metrics.

## Acceptance criteria

- Failed model/test events update one bounded project failure-memory artifact.
- Memory stores only a deterministic fingerprint, operation/kind/tool,
  failure mode/exit code, occurrence count, and bounded Session IDs.
- Error text, Prompt/source/review content, arguments, and output are never
  stored.
- Repeated failures across Sessions merge atomically and deterministically.
- `agent failures` renders recurring failures without private content.
- `agent metrics quality` reports planned/completed tasks/tests, completion
  rates, build/test and refactor call success, mean duration, and verified cost.
- Metrics are derived from validated plans, state, and telemetry; no estimates.

## Out of scope

- Semantic root-cause generation by a model.
- Remote databases or telemetry export.
- Unverified provider billing estimates.
