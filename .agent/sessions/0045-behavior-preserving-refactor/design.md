# Design

## Reused boundaries

- Reuse the final REFACTOR audit-chain loader and verifier.
- Reuse Provider configuration, process runners, Codex command resolution,
  source snapshots, evidence sanitization, and final test commands.
- Use only Python stdlib for hashing, JSON, temporary exchange, and atomic
  replacement; add no dependency.

## Flow

1. Validate the active REFACTOR Session and approved semantic-review chain.
2. Build a digest-bound request from the exact production source and review.
3. Generate and strictly validate one same-path replacement.
4. Atomically write source plus an optimistic automated-refactor state record.
5. Reuse final current-test/full-suite verification.
6. On verification failure, atomically restore the captured source/state.

## State contract

`automated_refactor` binds the file path, original digest, generated digest,
completion digest, and review digest. DONE records `automated_source_change`;
the legacy path records `no_source_change`.
