# Implementation

## Cycle 1

### RED

- Added focused contracts for Maven, Gradle Kotlin/Groovy, Node, canonical
  ordering, partial evidence, substring false positives, and initialization
  persistence.
- Focused run failed in eight cases because project profiles did not expose
  `quality_tools` and fresh metadata omitted the field.

### GREEN

- Added immutable quality-tool evidence to Java and Node project metadata.
- Reused strict Node script token matching and required both dependency and
  script evidence for ESLint and Prettier.
- Parsed Maven configuration once and matched exact plugin coordinates in
  canonical order.
- Matched anchored Gradle plugin declarations without treating comments or
  substrings as configuration.
- Persisted non-empty evidence in fresh `.agent/project.yml` metadata.
- Focused verification passed: 41 tests and 5 subtests.

### RED refinement

- Removed the optional group ID from the Checkstyle Maven fixture.
- The focused test failed because standard Maven plugins may omit the default
  `org.apache.maven.plugins` group.

### GREEN refinement

- Applied the documented Maven default plugin group only when the group is
  absent, retaining exact matching for every other coordinate.
- Focused verification passed again: 41 tests and 5 subtests; Ruff and Pyright
  also passed.

### RED comment-boundary refinement

- Added a Gradle fixture containing plugin-shaped text only inside line and
  block comments.
- The focused run failed because block-comment content matched the anchored
  declaration pattern.

### GREEN comment-boundary refinement

- Removed Gradle comments before applying exact declaration matching.
- Added the empty-metadata omission contract without changing write-once
  initialization behavior.

## Verification

- Ruff format: 183 files unchanged.
- Ruff check: passed.
- Pyright: 0 errors, 0 warnings.
- Pytest: 896 passed with 92.15% total coverage.
- Compileall and source/wheel package build: passed.
- All 57 Session state files are valid JSON; the active user Session remained
  byte-for-byte unchanged.
- Existing tests were not modified and the targeted secret scan returned no
  matches.
- Build, cache, coverage, bytecode, and Node fixture artifacts are covered by
  the existing `.gitignore`; no rule change is required.
