# Implementation

## Cycle 1: Semantic review contract (RED)

The focused test module failed during collection because no semantic review
core or adapter existed.

## Cycle 2: Typed review core (GREEN)

Added a source-only digest-bound request, closed typed findings and decisions,
strict source/path/line/duplicate/size/source-copy/credential validation, a
deterministic source-free report, and optimistic two-artifact recording that
keeps the Session in REVIEW.

## Cycle 3: Provider and state integration (GREEN)

Added strict JSON-command and isolated ephemeral Codex adapters, active-provider
composition, and `agent review semantic`. Approved semantic reports are
preserved by the existing invariant audit and enter REFACTOR with a distinct
audit decision; required changes remain in REVIEW. Legacy invariant-only review
continues unchanged.

## Cycle 4: Verification

All 750 tests pass with 93.18% coverage. Ruff, formatting, Pyright, build,
compile, Schema, secret, active-Session, and ignore audits pass. Existing ignore
rules cover the new atomic temporary files, so `.gitignore` needs no change.
