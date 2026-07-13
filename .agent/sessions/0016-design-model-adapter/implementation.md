# Implementation log

## Official Codex contract verification

The current Codex manual documents `codex exec` as the non-interactive surface,
`--ephemeral` for avoiding persisted rollout files, read-only sandboxing for
inspection-only automation, `--output-schema` for structured JSON Schema
results, and `--output-last-message` for a final result file.

## `.gitignore` baseline

Codex exchange files use the operating-system temporary directory with automatic
cleanup. They do not require repository ignore rules.

## Cycle 1: Design adapter contracts

### RED

The adapter test failed during collection because `design_adapter` did not
exist.

### GREEN

The provider-neutral JSON adapter serializes the exact six request fields and
strictly decodes the exact ten response fields. The Codex adapter creates a
private temporary Schema/result exchange, resolves the executable through the
injected resolver, and invokes the existing process boundary with ephemeral,
read-only, colorless, strict-output arguments. All 12 targeted tests passed.

## Cycle 2: Failure safety and redaction

Tests cover nonzero JSON/Codex exits, invalid JSON, non-object output,
missing/extra keys, invalid overview type, invalid collection type and item
type, extra Codex command tokens, and a missing result file. Error assertions
verify that sensitive request, stdout, and stderr content is not exposed.

Before RED, review found that the missing-output test accidentally used a
runner that created an output file. The user explicitly authorized correcting
only that fixture to use a successful runner that writes no result; the test
goal and assertion were unchanged.

## Cycle 3: Official contract and packaging review

The fresh official Codex manual confirmed the chosen non-interactive,
ephemeral, read-only, Schema-constrained, final-output-file invocation. The
implementation does not override the user's model, authentication, global
configuration, or environment.

## Current verification

- Ruff format and lint pass for all 73 files.
- Pyright reports zero errors and warnings for the Python 3.9 target.
- All 165 tests pass with 94.81% total coverage.
- Design-adapter coverage is 100%.
- Package compilation and source/wheel builds pass.
- Git diff whitespace validation passes.
- `.gitignore` already covers build outputs, caches, and temporary artifacts;
  no update is needed.
- The active PDF-export Session remains in `REQUIREMENT_REVIEW`.

The user explicitly authorized Ruff's mechanical formatting of
`tests/test_design_adapter.py`. No assertion or behavior changed.
