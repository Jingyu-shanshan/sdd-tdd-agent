# Design

`cycle_completion.py` stores an exact `implementation_completion` snapshot with
the ordered completed tests, final test ID, canonical GREEN evidence digest,
and final test/production artifact digests before entering REVIEW.

`implementation_review.py` validates that snapshot against the retained state,
renders a bounded deterministic invariant-review report, and coordinates
exclusive temporary files for `review.md` and `state.json`. The state records
both completion and report digests before entering REFACTOR.

The report is intentionally honest:

```text
audit integrity: passed
semantic automated review: deferred to v0.3
```

`cli.py` maps exact `agent review` to this deterministic service. It accepts no
model or test runner and does not overlap existing requirement/design/task
review subcommands.
