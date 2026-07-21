# Design

Build one immutable JSON-compatible dictionary from constants and the existing
Provider Registry. The plugin section documents the already-tested custom JSON
process contract and all model operations using it. The IDE section documents
three read-only CLI commands and established exit codes. The Provider section
is derived rather than duplicated.

The CLI only serializes the manifest with sorted keys and a trailing newline.
It requires no initialized workspace and has no injected side-effect boundary.
