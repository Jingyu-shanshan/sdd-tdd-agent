# Design

`tdd_cycle.py` clears every prior-cycle artifact when advancing GREEN to the
next ordered WRITE_TEST case.

`green_verification.py` exposes typed production-artifact revalidation for an
explicit TDD phase so completion can reuse the same path, symlink, and digest
policy.

`cycle_completion.py` validates final GREEN evidence against the current test,
revalidates both source artifacts around Session reads, proves the generated
plan has no remaining test, and atomically changes only the workflow state to
REVIEW.

`implementation_command.py` dispatches GREEN as follows:

```text
next test exists -> existing isolated test-source generation -> WRITE_TEST
no test remains  -> evidence/artifact completion -> REVIEW
```

The completion path invokes neither model nor test runner. The next-test path
uses the existing model boundary because generating that test is the next TDD
action.
