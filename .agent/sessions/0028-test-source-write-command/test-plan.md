# Test Plan

- Prove cycle preparation starts once, resumes without increment, advances after
  GREEN, and rejects RED/IMPLEMENT.
- Prove source collection is sorted, bounded, UTF-8, and limited to approved
  roots/markers plus the exact target while excluding hidden/symlink/binary and
  ignored runtime trees.
- Prove atomic writing creates or replaces only the planned file and removes its
  temporary sibling.
- Prove concurrent target create/change/delete, symlink ancestors, unsafe paths,
  and temporary collisions fail before replacement.
- Prove JSON orchestration sends current source and writes one file.
- Prove Codex orchestration runs from a temporary directory outside the project
  that is removed afterward.
- Prove configuration/model/write failures produce safe errors, do not write a
  generated test, and leave a recoverable cycle when already started.
- Prove exact `agent continue` output and invalid-state exit behavior.
