# Review

## Scope

The change adds one explicit REVIEW subcommand, isolated typed core/adapters,
one packaged Prompt, a minimal compatible extension to invariant/final audit
decisions, focused tests, and documentation. It does not modify target source.

## Compatibility

Plain `agent review` retains its deterministic no-model behavior and exact
legacy report/state shape when no semantic review exists. Existing completed
Sessions and refactor verification continue to accept
`invariant_review_passed`; the new decision is accepted only with a valid
approved semantic record and matching report digest.

## Safety

The model receives exactly two digest-bound sources and no SDD/state/output.
Findings are constrained to visible locations and bounded safe text. Source
copy, secret-like output, duplicate findings, invalid decisions, stale files,
symlinks, collisions, and concurrent changes fail without advancing state.

## Verification

Focused and full local gates pass. Hosted workflows are required after push.
