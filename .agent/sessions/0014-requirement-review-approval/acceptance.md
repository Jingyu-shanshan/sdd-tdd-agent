# Acceptance criteria

- [ ] The active analyzed requirement can be displayed without mutation.
- [ ] Explicit approval changes only `REQUIREMENT_REVIEW` to `DESIGN`.
- [ ] Explicit rejection records a normalized non-empty reason and returns to
  `ANALYSIS`.
- [ ] Decisions preserve existing Session state data.
- [ ] Invalid, unsafe, mismatched, or wrongly staged Sessions fail safely.
- [ ] CLI output and exit codes are deterministic.
- [ ] Existing tests and active product Session state remain unchanged.
- [ ] No new dependency, secret, hidden mutation, or unrelated change exists.
- [ ] `.gitignore` covers the atomic temporary file pattern.
