# Design

## Workspace boundary

Add a focused `angular_workspace` module that strictly parses root
`angular.json` with duplicate-key detection. It returns immutable workspace and
project records without mutating files. A project path must be normalized,
relative, traversal-free, and its source root must stay within its configured
project root. Angular module proposals must in turn stay within one of those
verified source roots, so workspace-root applications and monorepo libraries
share one boundary rule.

Design-request loading first reuses verified project detection. A TypeScript
request whose framework is Angular then loads the workspace context and selects
`v3-angular`. Non-Angular TypeScript remains on `v2-typescript`; projects
without supported TypeScript configuration evidence retain v1.

## Typed proposal extension

Extend `DesignGenerationRequest` with optional `angular_context` and
`DesignProposal` with default-empty `angular_constraints`. Use
`AngularArchitectureConstraint(area, decision, rationale, verification)`.

The JSON output Schema keeps all existing fields unchanged and exposes
`angular_constraints` as an optional strict array. Angular domain validation
requires at least one record; other workflows reject Angular records.

## Validation

Constraint areas use a closed vocabulary covering component boundaries,
dependency injection, templates, routing, state management, asynchronous
behavior, and testing. Each area may appear once. All decision, rationale, and
verification values must be non-empty strings.

## Rendering

Angular requests append deterministic `Angular workspace` and
`Angular architecture constraints` sections after the TypeScript sections.
Project records retain their configuration order while field order is fixed.

## Compatibility

Request payloads include `angular_context` only when present. Existing generic,
Java, and non-Angular TypeScript payloads remain byte-for-byte structurally
compatible. The decoder continues accepting legacy optional-field omissions
outside workflows that semantically require them.
