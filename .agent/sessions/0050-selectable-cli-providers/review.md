# Review

## Result

Accepted pending final hosted CI. The implementation adds one operation-neutral
normalization boundary and reuses every existing workflow's typed request,
response, state, and human-review behavior.

Claude and Cursor invocations are single-executable, non-interactive, bounded,
and shell-free. Provider/session/output fields are neither persisted nor exposed
through errors. Copilot is not promoted without its distinct JSONL contract.
