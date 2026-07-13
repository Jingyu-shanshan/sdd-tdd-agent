# Acceptance criteria

- [x] The active analyzed requirement can be displayed without mutation.
- [x] Explicit approval changes only `REQUIREMENT_REVIEW` to `DESIGN`.
- [x] Explicit rejection records a normalized non-empty reason and returns to
  `ANALYSIS`.
- [x] Decisions preserve existing Session state data.
- [x] Invalid, unsafe, mismatched, or wrongly staged Sessions fail safely.
- [x] CLI output and exit codes are deterministic.
- [x] Existing tests and active product Session state remain unchanged.
- [x] No new dependency, secret, hidden mutation, or unrelated change exists.
- [x] `.gitignore` covers the atomic temporary file pattern.
