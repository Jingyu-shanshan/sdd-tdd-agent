# Requirement

## User request

Generate exactly one executable test source for the active incremental TDD
cycle while preserving the platform's context-isolation rules.

## Requirements

- Load only an active `WRITE_TEST` case from an IMPLEMENTATION Session.
- Supply the test author with the approved requirement, approved design,
  current test case, and explicitly provided current source snapshots.
- Never supply tasks, the complete test plan, future tests, process output, or
  hidden workspace files to the test-author model.
- Load a versioned Prompt from a packaged file.
- Expose a typed, dependency-injected generator boundary.
- Validate source snapshot paths, uniqueness, content, and size before model
  execution.
- Require generated output to match the current test ID and planned test-file
  path exactly and to contain non-empty source without null bytes.
- Support the provider-neutral JSON command protocol and ephemeral read-only
  Codex execution through strict JSON Schemas.
- Redact Prompt, specifications, source, output, and provider stderr from safe
  public errors.
- Do not mutate Session state or project files in this increment.

## Out of scope

- Selecting or starting a new TDD cycle.
- Writing the generated test source.
- Running the test to prove RED.
- Generating or modifying production code.
