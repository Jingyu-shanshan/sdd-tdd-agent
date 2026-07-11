# Test plan

## Cycle 1: Happy path

Current test: call `hello` with an in-memory text stream and assert its exact
contents are `Hello, World!\n`.

After the unit test is GREEN, add one integration test that invokes the module
command and verifies its exit status and exact stdout. Boundary, exception, and
regression cases are deferred because the current requirement defines only one
command and one happy path.
