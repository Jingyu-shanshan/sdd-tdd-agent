# Test Plan

- Start with no `.agent` workspace and initialize a strict Vitest project.
- Create a feature and prove ANALYSIS -> REQUIREMENT_REVIEW -> DESIGN ->
  DESIGN_REVIEW -> TASK_BREAKDOWN -> TASK_REVIEW -> TEST_GENERATION ->
  IMPLEMENTATION.
- Prove successive `agent continue` calls write one test, observe attributable
  RED, write minimal production source, pass current/full suite, and exhaust the
  plan into REVIEW.
- Prove `agent review` enters REFACTOR and exact `agent refactor` enters DONE.
- Assert five target-process calls: RED current; GREEN current/full; final
  current/full, with 15/60-second timeout separation.
- Assert six model calls only and that Blind production input excludes unique
  requirement content.
- Assert final state includes completion, implementation-review, refactor, and
  final-verification records.
