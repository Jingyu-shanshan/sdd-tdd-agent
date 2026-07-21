# Design

## Boundary derivation

Load the current typed test case from the trustworthy RED cycle. A generic case
uses `src`; an Angular case resolves its project name against the strictly
parsed root `angular.json` and uses exactly that project's configured
`sourceRoot`.

## Blind request

Add an immutable tuple of normalized production source roots to the request.
Angular monorepo requests use a dedicated packaged Prompt and expose that tuple
in the provider payload. Generic v1 payloads remain byte-shape compatible and
do not gain the conditional field.

## Filesystem enforcement

Parameterize the existing production path validator, collector, and atomic
writer with the request roots. A path must be a descendant of one allowed root
and still satisfy all existing extension, hidden-path, test-path, normalization,
size, count, symlink, and optimistic-concurrency rules.

## Audit-chain compatibility

Generic artifact records retain their exact three-field shape. Non-root Angular
records additionally bind the configured `source_root`; GREEN and final
REFACTOR verification use that stored boundary when revalidating the path and
digest. This keeps old Sessions readable while preventing boundary widening.

