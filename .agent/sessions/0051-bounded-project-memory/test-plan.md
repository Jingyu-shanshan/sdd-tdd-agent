# Test Plan

- Load the initialized three-file memory and preserve exact content.
- Produce a stable digest that changes when reviewed memory changes.
- Reject missing, empty, unsafe, invalid UTF-8, oversized, and changed files.
- Render only digest, filenames, and byte sizes.
- Report CLI errors without content or traceback.
- Preserve initialization and requirement-analysis behavior.
