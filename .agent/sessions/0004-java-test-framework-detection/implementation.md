# Implementation log

## Quality-rule baseline

- Added root `AGENTS.md` exactly as supplied by the user.
- Added development-only pytest, pytest-cov, Ruff, and Pyright dependencies.
- Enforced 80% minimum coverage, Ruff line length 88, and Python 3.9 typing.
- With explicit human approval, changed two existing non-null assertions to an
  equivalent form understood by Pyright.
- Baseline result: 10 tests passed, 91.07% coverage, Ruff and Pyright passed.

## Cycle 1: Basic Maven JUnit 5 detection

### RED

Command: `uv run pytest`

Result: failed as expected with `AttributeError` because `ProjectProfile` had no
`test_frameworks` field. The previous 10 tests passed and coverage remained
91.07%.

### GREEN

Command: `uv run pytest`

Result: passed, 11 tests with 91.30% coverage. The immutable profile now records
JUnit 5 from a valid non-namespaced Maven dependency.

## Cycle 2: Standard Maven namespace

### RED

Command: `uv run pytest`

Result: the namespaced POM test failed as expected with an empty framework
tuple; the other 11 tests passed.

### GREEN

Command: `uv run pytest`

Result: passed, 12 tests with 91.03% coverage. XML matching now uses local tag
names, preserving the same dependency-level recognition rule.

## Cycle 3: Persist JUnit 5 metadata

### RED

Command: `uv run pytest`

Result: failed as expected because `project.yml` contained language and build
tool metadata but no `test_frameworks` section; the other 12 tests passed.

### GREEN

Command: `uv run pytest`

Result: passed, 13 tests with 91.36% coverage. Initialization renders a YAML
list only when the detected framework tuple is non-empty.

### Negative acceptance coverage

Added a JUnit 4 dependency example. It passed without production changes,
confirming that the existing group and artifact rule does not over-classify it.
The suite reached 14 passing tests and 92.59% coverage.

### Refactor

Extracted typed project-metadata rendering and exclusive first-write helpers
from `initialize_project`. This keeps initialization orchestration focused and
replaces an empty exception body with an explicit idempotent return. All 14
tests remained GREEN and coverage increased to 93.10%.
