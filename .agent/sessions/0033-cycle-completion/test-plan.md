# Test Plan

- Prove GREEN with another test selects only the next dependency-ready case,
  invokes only test-source generation, enters WRITE_TEST, and clears all stale
  per-cycle evidence.
- Prove GREEN with the exact completed plan invokes no model or test runner,
  clears `current_task`, preserves audit evidence, and enters REVIEW.
- Prove deterministic CLI output for both next-test generation and completion.
- Prove missing/extra/mismatched GREEN evidence fields, commands, return codes,
  streams, IDs, and sanitization fail without mutation.
- Prove changed, missing, stale, or symlinked test/production artifacts prevent
  REVIEW.
- Prove concurrent Session updates and atomic temporary collisions preserve
  GREEN.
- Prove a remaining plan case prevents implementation completion.
- Prove existing no-progress/WRITE_TEST/RED/IMPLEMENT dispatch is unchanged.
