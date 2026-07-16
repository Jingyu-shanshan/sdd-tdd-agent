# Design

`red_execution.py` owns four boundaries:

- `TestCommandRunner` and `SystemTestCommandRunner` execute already-tokenized
  commands without a shell.
- Source-artifact record/validation binds state to the generated file digest.
- RED classification requires non-zero, non-signal execution, rejects known
  no-test/option failures, and requires current-test identity in output.
- Evidence sanitization and an atomic state update preserve only bounded safe
  diagnostic context.

`load_test_command_timeout` strictly reads the new config key. It does not reuse
or infer the model timeout.

`implementation_command.py` selects the next IMPLEMENTATION action:

```text
no matching source marker -> generate/write one test -> WRITE_TEST
matching source marker    -> execute current test -> RED
```

`agent continue` keeps its existing first-step output. The second step renders:

```text
RED confirmed: feature-1 (TC1, exit 1)
```

The next increment will consume `red_evidence` to construct the Blind developer
context and generate minimal production changes.
