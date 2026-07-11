# Acceptance criteria

- [x] A complete eight-file Session is created exclusively.
- [x] The exact normalized request and `ANALYSIS` state are persisted.
- [x] Project metadata activates the new Session without unrelated changes.
- [x] `agent feature` reports the new ID and exits 0.
- [x] Empty requests and unsafe IDs are rejected before mutation.
- [x] `.gitignore` covers generated caches/logs/metrics but not SDD records.
- [x] Ruff, Pyright, pytest, coverage, and Python 3.9 checks pass.
