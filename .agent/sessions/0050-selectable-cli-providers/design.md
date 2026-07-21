# Design

## Shared structured CLI boundary

Keep every existing JSON workflow adapter unchanged. A small injected process
runner decorator translates its configured single executable into the verified
Claude or Cursor invocation, preserves the typed JSON request on stdin, and
normalizes the successful provider envelope back to the JSON object expected by
the existing adapter.

The decorator is protocol-driven and operation-neutral. It validates a bounded
JSON object with duplicate-key rejection, requires the documented successful
result envelope, then accepts either a structured object or an object encoded in
the result string. Errors use fixed safe messages and never include process or
model content.

## Composition

`claude-exec` uses `claude -p --output-format json --permission-mode plan
--no-session-persistence`. `cursor-exec` uses `cursor-agent -p --output-format
json` and deliberately omits `--force`. All active workflow composition points
decorate only their existing JSON adapter runner; Codex retains its dedicated
ephemeral read-only file exchange.

## Registry and installation

Registry definitions provide the exact protocol, executable, supported target
platforms, and official shell-installer URL. The existing guarded installer
continues to split download and execution into separate tokenized shell-free
processes and verifies `--version` before selection.
