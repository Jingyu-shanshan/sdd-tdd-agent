# Implementation

## Cycle 1: RED contracts

- Added contracts for strict porcelain parsing, read-only preparation, exact
  staging/commit commands, approval binding, recovery, and CLI composition.
- Verified the first run failed because `git_integration` did not exist.

## Cycle 2: Preparation GREEN

- Added a typed injected Git runner and production `shell=False` runner.
- Reused current GREEN test/production artifact validation for exact paths.
- Added scoped NUL-delimited status parsing and risk approval requests without
  index mutation.

## Cycle 3: Commit GREEN

- Required approved/not-required matching digests before Git mutation.
- Added exact pathspec staging, cached-name validation, second status/artifact
  validation, `commit --only`, HEAD verification, and digest archive.
- Added a real-repository test proving unrelated staged changes remain staged
  and outside the commit.

## Cycle 4: Verification

- `ruff check .`: passed.
- `ruff format --check .`: 174 files already formatted.
- `pyright`: 0 errors, 0 warnings, 0 informations.
- `pytest`: 851 passed; total coverage 92.25%.
- Critical Git integration coverage: 90%; change approval remains 91%.
- Python compilation and `uv build`: passed.
- Real Git commit isolation, secret, diff, active-Session, and ignore audits:
  passed.
- `.gitignore` requires no change: build/cache artifacts and atomic approval
  temporary files are covered; archived approvals are intentional evidence.
