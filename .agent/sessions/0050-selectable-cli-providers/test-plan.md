# Test Plan

- Registry/list output distinguishes ready Claude/Cursor from planned Copilot.
- Selection writes exact protocol/executable and preserves unrelated config.
- Claude and Cursor invocations contain only the verified non-interactive flags.
- Provider result objects and JSON result strings normalize successfully.
- Duplicate keys, excessive output, failure envelopes, invalid JSON, and
  non-object nested results fail with content-free errors.
- Nonzero provider exit results retain existing safe adapter error behavior.
- Guarded official installer plans work through injected process/locator tools.
- Existing Codex, custom JSON, and all full quality gates remain green.
