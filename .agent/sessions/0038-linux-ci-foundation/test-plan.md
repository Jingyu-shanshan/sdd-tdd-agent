# Test Plan

## RED

- Prove hosted CI is absent by requiring its explicit Python matrix, shell
  matrix, quality commands, least privilege, and immutable action pins.
- Prove Linux Mint CI is absent by requiring a manual-only workflow, exact
  self-hosted labels, platform-doctor assertions, and no host package mutation.

## GREEN

- Implement only the workflow declarations needed by the failing contracts.
- Re-run the focused workflow contract tests.

## Regression

- Run `ruff check .`.
- Run `ruff format --check .` after applying repository formatting.
- Run `pyright`.
- Run the full pytest suite with configured coverage enforcement.
- Build the Python distribution and compile production modules.
- Validate JSON, scan tracked files for secret-shaped content, confirm active
  Session preservation, and inspect ignored/untracked files.
