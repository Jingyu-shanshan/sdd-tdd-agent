# Design

`tdd_cycle.py` parses the deterministic `# Test Generation Plan` artifact into
existing `TestCasePlan` values and reuses core semantic validation against the
generated task IDs.

`select_next_test_case` is read-only. `start_next_tdd_cycle` validates state and
progress, then atomically records:

```json
{
  "current_task": "T1",
  "current_cycle": 1,
  "tdd_cycle": {
    "current_test": "TC1",
    "phase": "WRITE_TEST",
    "completed_tests": []
  }
}
```

`BlindDevelopmentContext` intentionally has no requirement/design/plan fields.
It accepts only the selected case, explicitly supplied production snapshots,
and compiler/test outputs for the later developer agent.
