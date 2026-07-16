# Design

`test_execution.py` gains a typed full-suite plan derived from the same strict
project/framework evidence as the current-test plan:

```text
Maven    -> <launcher> test
Gradle   -> <launcher> test
Jest     -> <manager test prefix> --runInBand
Vitest   -> <manager test prefix> --run
Angular  -> <manager test prefix> --watch=false
```

`execution_config.py` strictly loads the separate suite timeout.

`green_verification.py` owns IMPLEMENT artifact validation, two-gate process
execution, retry classification, evidence sanitization, and atomic state
updates. It uses the existing injected `TestCommandRunner` and shell-free
system implementation.

State transitions:

```text
IMPLEMENT -- current trusted failure --> RED (retry evidence)
IMPLEMENT -- current pass, suite trusted failure --> RED (regression evidence)
IMPLEMENT -- both pass --> GREEN (completed prefix + green evidence)
IMPLEMENT -- infrastructure/concurrency failure --> IMPLEMENT unchanged
```

`implementation_command.py` dispatches IMPLEMENT to this verifier. GREEN is
left for the review/refactor increment.
