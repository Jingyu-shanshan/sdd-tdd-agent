# Design

## Evidence reconciliation

Update only the four completed task records whose successful GitHub CI and
toolchain runs were observed after their commits. Identify each result by its
immutable commit prefix.

## Architecture reconciliation

Replace the obsolete statement that semantic review is future work with the
implemented optional, typed, isolated, approval-gated workflow. Do not widen
the public API or runtime scope.

## Release audit

Use repository-native quality commands and read-only audits. Treat every check
as fail-closed. The active user Session is an invariant, not an audit fixture to
rewrite. No new dependency or generated artifact is required.

## External boundaries

The Copilot CLI's documented JSONL transport is insufficient by itself for a
strict result adapter without documented event fields. The real Linux Mint job
also requires owner-provided infrastructure. Both boundaries remain explicit
instead of being reported as completed behavior.
