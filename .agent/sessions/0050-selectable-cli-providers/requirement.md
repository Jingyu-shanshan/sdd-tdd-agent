# Requirement

## Goal

Make Claude Code and Cursor selectable single-agent providers through their
verified non-interactive CLI contracts while preserving every existing typed
SDD/TDD workflow and human gate.

## Acceptance criteria

- The Provider Registry reports Claude Code and Cursor as adapter-ready on
  macOS and Linux Mint; GitHub Copilot remains planned.
- Selection writes one explicit executable and provider-specific protocol.
- Every existing JSON workflow can use either provider without duplicating its
  request or response validation.
- Claude runs in print, JSON, plan-permission, non-persistent mode.
- Cursor runs in print JSON mode without force/write authorization.
- Provider result envelopes and nested JSON reject malformed, duplicate,
  oversized, unsuccessful, or non-object output without exposing content.
- Interactive missing-CLI selection offers the existing guarded official
  installer flow; non-interactive selection never installs.
- Existing Codex and custom JSON behavior remains compatible.

## Out of scope

- GitHub Copilot selection before its JSONL event contract has dedicated tests.
- Authentication, credential storage, licensing decisions, or background
  sessions.
- Allowing a provider CLI direct write access through these adapters.
