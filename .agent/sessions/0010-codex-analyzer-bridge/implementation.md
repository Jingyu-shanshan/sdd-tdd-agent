# Implementation log

## Documentation verification

The official manual helper reached the OpenAI endpoint but could not validate
the response because its integrity header was absent. The official Docs MCP was
installed for use after application restart. Local `codex exec --help` from CLI
0.144.0-alpha.4 verified `--ephemeral`, `--sandbox`, `--output-schema`,
`--output-last-message`, `--cd`, and stdin prompt support.

## `.gitignore` baseline

The bridge design uses operating-system temporary files outside the repository.
No generated bridge artifact should require a new ignore pattern.

## Cycle 1: Codex adapter exchange

### RED

The first adapter test failed during collection because
`CodexExecRequirementAnalyzer` did not exist.

### GREEN

The new adapter writes the strict analysis Schema into a private temporary
directory, constructs the verified ephemeral/read-only Codex command, supplies
request JSON through stdin, and decodes only the final-message file. The
exchange test passed without a real model call.

## Cycle 2: Protocol configuration and composition

### RED

Five configuration tests showed the old parser ignored protocol selection, and
the composition test showed it still selected the generic JSON adapter.

### GREEN

`CommandAnalyzerConfig` now carries a validated protocol with the compatible
`json-command` default. The strict config parser accepts only `json-command` or
`codex-exec`, rejects duplicates and invalid Codex command shapes, and the
composition service selects the Codex adapter explicitly. Existing JSON command
tests remained unchanged and passed.

## Failure paths and refactor

Tests cover extra command tokens, nonzero Codex exit codes, and missing output.
Errors exclude prompt, stdout, and stderr content. No further refactor was
needed; temporary-file exchange, process execution, domain decoding, workflow
mutation, and CLI dispatch remain separate responsibilities.

## Final verification

- Ruff lint and formatting pass.
- Pyright reports zero errors or warnings.
- All 74 tests pass with 95.64% total coverage.
- Codex adapter coverage is 99%; analyzer composition coverage is 96%.
- Python 3.9 compilation and source/wheel builds pass.
- The repository config parses as `codex-exec`, executable `codex`, 300 seconds.
- All 11 Session state files are valid JSON without duplicate keys.
- Build, coverage, Python, and agent runtime artifacts remain ignored.
- The active support-PDF Session remains unchanged in `ANALYSIS`.

## Cycle 4: Reported terminal startup failure

### Diagnosis

The reported command failed before Codex startup. The Codex App execution
environment could resolve `codex`, but an ordinary terminal did not necessarily
inherit `/Applications/ChatGPT.app/Contents/Resources` in PATH. The executable
itself was present and runnable.

### RED

New resolver tests failed during collection because no typed Codex command
resolver existed and the Adapter could not accept one.

### GREEN

`SystemCodexCommandResolver` now preserves a working PATH command. When and only
when the configured name is exactly `codex` and PATH lookup fails, it selects an
executable verified at the macOS ChatGPT bundle path. Custom commands remain
unchanged. The resolver is injected into the Adapter for deterministic tests.

A subprocess with the ChatGPT resource directory deliberately removed from
PATH resolved the bundled executable and ran `codex-cli 0.144.0-alpha.4`
successfully without a model request.
