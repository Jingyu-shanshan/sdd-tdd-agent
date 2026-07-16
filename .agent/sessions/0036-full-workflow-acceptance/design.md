# Design

Add one acceptance test with two stateful injected fakes:

- a provider-neutral model runner returns strict structured results for the six
  model boundaries in their required order;
- a test runner returns one attributable RED result followed by four passing
  current/full-suite results while recording commands and timeouts.

The test creates a fresh Vitest project, invokes the real `main` CLI boundary
for every command, and resolves the generated Session ID from project status.
It observes state after every step and verifies the final digest-bound records.

Unique requirement content must be visible to the isolated test-generation
context but absent from the Blind production-generation request. Review and
refactor must add no provider calls.
