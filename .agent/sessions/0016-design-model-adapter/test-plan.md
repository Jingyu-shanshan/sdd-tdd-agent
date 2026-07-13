# Test plan

## JSON command

- Record command, timeout, and parsed stdin payload.
- Decode a complete valid proposal.
- Reject nonzero exit, invalid JSON, non-object response, missing/extra keys,
  non-string overview, non-array fields, and non-string array members.
- Verify errors do not contain request or process content.

## Codex exec

- Inspect the generated JSON Schema.
- Assert ephemeral/read-only/color/output/cd/stdin command tokens.
- Verify the configured executable is resolved through an injected resolver.
- Reject multiple command tokens, nonzero exit, and missing result files.
- Verify the temporary exchange directory is cleaned.

## Regression and quality

- Run full pytest with coverage, Ruff format/check, and Pyright.
- Compile and build source/wheel packages.
- Validate all Session JSON without duplicate keys.
- Review `.gitignore` and preserve the active PDF Session.
