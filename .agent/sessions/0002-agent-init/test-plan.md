# Test plan

1. Happy path: initialize an empty temporary project and inspect directories.
2. Happy path: inspect generated metadata and project identity.
3. Integration boundary: dispatch `init` through the CLI with an injected root.
4. Regression: edit metadata, initialize again, and prove the edit survives.

Missing arguments, unsupported commands, project-tool detection, and malformed
existing workspaces remain outside this session.

