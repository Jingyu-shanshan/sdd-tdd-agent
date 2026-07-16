# Design

`refactor_completion.py` loads the active REFACTOR state and validates the
digest chain:

```text
review.md -> implementation_review -> implementation_completion
          -> GREEN evidence -> test/production artifact records -> files
```

It extracts only the already validated tokenized current/full-suite commands,
runs them sequentially through the injected shell-free `TestCommandRunner`, and
revalidates the entire immutable context after each process.

Both zero exits produce sanitized bounded `final_verification` evidence and a
`refactor` record with `mode=no_source_change`. One atomic state replacement
enters DONE. No source writer or model boundary exists in this stage.

`cli.py` maps exact `agent refactor` to the service and uses the existing system
test runner by default.
