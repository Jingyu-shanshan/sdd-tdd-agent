# Test plan

- Verify exact JSON command, timeout, eight-field request, and nested result.
- Reject malformed JSON, non-object top-level/cases, wrong keys, invalid scalars,
  invalid lists, and non-string members.
- Verify safe process-exit errors.
- Inspect Codex top-level/case Schema, flags, resolver, request, output, cleanup.
- Reject extra Codex command tokens and missing structured output.
- Run Ruff, Pyright, full pytest/coverage, compile, build, JSON, and Git checks.
