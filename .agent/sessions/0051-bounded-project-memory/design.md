# Design

Reuse `.agent/project.yml`, `.agent/architecture.md`, and
`.agent/conventions.md` as the canonical human-reviewable memory. A standard-
library loader reads the three files, rejects unsafe paths and invalid content,
enforces one total byte limit, confirms the files did not change during the
read, and hashes a canonical ordered snapshot.

Requirement analysis consumes the resulting typed strings instead of reading
the same files independently. A read-only CLI view renders only filenames,
byte counts, and the snapshot digest.
