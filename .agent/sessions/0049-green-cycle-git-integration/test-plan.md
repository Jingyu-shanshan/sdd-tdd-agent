# Test Plan

- Preparation accepts only active digest-valid GREEN artifacts.
- Porcelain added/modified/deleted records map to exact typed changes.
- Missing, duplicate, renamed, malformed, extra, or nonzero status fails.
- Preparation never stages or commits and creates a pending exact approval.
- Rejected, pending, stale, or changed approval blocks index mutation.
- Exact add/cached-name/commit/rev-parse command ordering is enforced.
- Artifact/status changes between steps fail before commit.
- Commit failure preserves the active approval; archive collision fails early.
- CLI output is deterministic and never includes Git stdout/stderr.
- Production runner uses explicit cwd, timeout, capture, and `shell=False`.
