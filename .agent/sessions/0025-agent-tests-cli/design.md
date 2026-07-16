# Design

Add `test_command.py` with `generate_active_test_plan`. It loads project status
before configuration, chooses `JsonCommandTestPlanGenerator` or
`CodexExecTestPlanGenerator`, then delegates to `run_test_generation`.

The exact CLI vector `agent tests` uses the injected/default runner and renders:

```text
Test plan ready for implementation: <session-id> (IMPLEMENTATION)
```

Value/configuration/adapter errors use the existing safe CLI contract. No
validation or filesystem behavior is duplicated in dispatch.
