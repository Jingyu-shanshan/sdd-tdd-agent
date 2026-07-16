# Requirement

## User request

Establish the one-test-at-a-time implementation cycle and Blind TDD development
context after test-plan generation.

## Requirements

- Parse only deterministic generated test-plan cases.
- Select the first incomplete case in plan order.
- Require IMPLEMENTATION state and all prior approvals.
- Require completed dependencies before selecting a case.
- Atomically record current task/test, cycle number, phase `WRITE_TEST`, and
  completed test IDs without changing the workflow state.
- Reject duplicate starts until the prior cycle reaches GREEN.
- Provide a typed Blind development context containing only current test,
  production snapshots, compile output, and test output.
- Exclude requirement, design, tasks, and future tests from that context.
- Add no model adapter, file writer, runner, or CLI yet.

## Out of scope

- Test source generation and RED execution.
- Production source modification and GREEN verification.
