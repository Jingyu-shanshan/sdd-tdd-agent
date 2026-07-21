# Implementation

## Cycle 1: Workspace contract (RED/GREEN)

The first focused run failed during collection because no Angular workspace
boundary existed. Added immutable project/workspace records and a strict,
read-only `angular.json` loader; all eight parsing contracts passed.

## Cycle 2: Angular design contract (RED/GREEN)

The second focused run failed because the typed Angular architecture constraint
did not exist. Added conditional `v3-angular` context/Prompt selection, optional
strict adapter fields, semantic validation, and deterministic rendering.

## Cycle 3: Monorepo source boundary (RED/GREEN)

A focused test proved that the existing top-level `src/**` rule rejected valid
Angular library modules. TypeScript module validation now uses verified Angular
project source roots while non-Angular TypeScript retains its original `src/**`
boundary. Focused Angular, TypeScript, Schema, and compatibility tests pass.

## Cycle 4: Verification

All 707 tests pass with 93.81% coverage. Ruff check, Ruff format verification,
and Pyright pass. The distribution builds with the Angular Prompt and workspace
module included; production compilation, Agent JSON, design Schema, secret,
active-Session, and ignored-file audits pass. Existing ignore rules cover every
generated artifact, so `.gitignore` needs no change.
