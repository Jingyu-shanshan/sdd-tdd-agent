# Test Plan

- Prove exact valid REFACTOR runs current test then full suite with configured
  15/60-second fixture timeouts, records sanitized evidence, and enters DONE.
- Prove exact CLI output and absence of model/source-writing boundaries.
- Prove current failure prevents the suite and preserves byte-identical state.
- Prove suite failure, signal, timeout, and startup failure preserve REFACTOR.
- Prove changed, missing, stale, unsafe, or symlinked final test/production
  artifacts prevent process execution or DONE.
- Prove review report, review record, completion snapshot, GREEN evidence, and
  command tampering fail before execution.
- Prove state/file changes during either process prevent DONE.
- Prove output is sanitized/bounded and atomic temporary collisions preserve
  both REFACTOR and pre-existing ownership markers.
- Prove non-REFACTOR and missing active Sessions fail safely.
