# Requirement

## User request

Continue the full incremental SDD/TDD workflow after trustworthy RED by
generating and safely writing only the minimal production source needed for the
current failing test.

## Requirements

- Build a typed Blind development context containing only the current test
  plan/source, current production source, and sanitized compile/test output.
- Do not load or expose requirement, design, task, full-plan, future-test, or
  raw Session content to the production-code model.
- Load the current test only when the cycle is RED and its recorded source
  digest still matches before and after context construction.
- Store a versioned production-source Prompt in the package, separate from
  business and orchestration logic.
- Add provider-neutral JSON and ephemeral read-only Codex adapters behind a
  typed injected generator boundary.
- Require an exact result containing current test ID, one production file path,
  and complete non-empty UTF-8 source content.
- Permit writes only below `src/` using supported source suffixes. Reject tests,
  hidden/protected paths, symlinks, traversal, configurations, and unsupported
  files.
- Preserve an existing production target unless its captured content remains
  unchanged; allow one safe new production source and write atomically.
- Revalidate RED state and the current test artifact before writing.
- After a successful write, atomically transition RED to IMPLEMENT and record
  the production file ID/path/SHA-256 without storing source content in state.
- Extend `agent continue` to dispatch RED to production generation and render
  deterministic success/error output without invoking the test runner.
- Clear stale production evidence when a new TDD cycle starts.
- Keep the real active user Session and unrelated files unchanged.

## Out of scope

- Running the current test for GREEN.
- Running compilation or the full regression suite.
- Multiple production-file changes in one cycle.
- Dependency/configuration changes, database migrations, public API redesign,
  deletions, or refactoring.
