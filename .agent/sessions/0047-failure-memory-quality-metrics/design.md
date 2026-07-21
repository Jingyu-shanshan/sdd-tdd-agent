# Design

## Failure memory

The telemetry recorder calls one stdlib-only failure-memory function for failed
events. A canonical fingerprint merges identical operation/kind/tool/failure
modes across Sessions. The bounded JSON artifact uses optimistic atomic replace
under `.agent/memories/failures.json`.

## Quality projection

Expose all validated test-plan cases through the existing TDD parser. Combine
their task/test identities with the trusted completed-test prefix and validated
telemetry events. Derive rates only from exact counts; return unavailable when
there is no denominator or complete verified cost data.

## Compatibility

No state Schema or Provider/test-runner contract changes. Existing telemetry
rendering remains unchanged; quality and failure views use new subcommands.
