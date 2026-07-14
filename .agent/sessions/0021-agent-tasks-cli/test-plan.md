# Test plan

## Application service

- Build an isolated approved `TASK_BREAKDOWN` Session with tracked context.
- Verify JSON configuration sends the request through the configured command and
  produces `TASK_REVIEW` plus rendered task output.
- Verify Codex configuration uses the injected resolver and structured output.
- Verify a missing active Session fails before configuration or process use.

## CLI

- Verify exact successful stdout and exit code for `agent tasks`.
- Verify incomplete configuration produces safe stderr, exit code 2, and no
  process invocation.

## Quality

- Run targeted RED and GREEN tests before the full suite.
- Run Ruff format/check, Pyright, pytest with coverage, compile, and build.
- Verify Session JSON has no duplicate keys and `.gitignore` remains sufficient.
- Preserve the active PDF Session in `REQUIREMENT_REVIEW`.
