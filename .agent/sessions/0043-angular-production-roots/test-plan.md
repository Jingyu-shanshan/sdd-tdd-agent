# Test Plan

## RED

- An Angular library current test resolves only its configured monorepo source
  root and selects a dedicated packaged Prompt.
- Collection sees production source only under that root.
- Provider exchange names the exact writable root without exposing workspace
  configuration or SDD content.
- Validation and writing accept the configured root and reject a sibling
  Angular project's path.
- Generic request and payload behavior remains unchanged.

## GREEN

- Add typed source-root derivation and request metadata.
- Parameterize production source path, collection, validation, and writing.
- Bind non-root Angular state records and downstream digest validation.

## Regression

- Run Ruff lint/format, Pyright, full pytest coverage, build, compile, schema,
  secret, Session-preservation, and ignored-file audits.
- Push and require both hosted workflows to pass.

