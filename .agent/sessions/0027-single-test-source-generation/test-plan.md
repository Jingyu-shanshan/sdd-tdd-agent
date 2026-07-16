# Test Plan

- Prove request loading exposes requirement/design, current test, and explicit
  source snapshots without tasks, future tests, or execution output.
- Reject inactive, wrong-phase, mismatched, unsafe, duplicate, empty, oversized,
  or hidden source input before model execution.
- Accept one valid generated source bound to the current test and exact planned
  file.
- Reject mismatched IDs/paths, empty content, null bytes, oversized content, and
  non-model result values.
- Prove JSON command payload shape, exact response decoding, timeout propagation,
  non-zero exit handling, and error redaction.
- Prove Codex uses structured output, a read-only ephemeral sandbox, the project
  root, a strict Schema, and removes its exchange directory.
