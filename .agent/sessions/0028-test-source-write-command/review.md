# Review

The command validates configuration before starting a cycle, making configuration
errors mutation-free. Once a cycle starts, Provider or write failures leave a
recoverable `WRITE_TEST` state and no generated target. A resumed cycle is
read-only until the validated test source is ready.

The collector cannot read `.agent`, `.git`, dependency/cache trees, hidden
files, binaries, or direct/ancestor symlinks. The writer detects concurrent
target create/change/delete, validates the planned path twice, uses an exclusive
atomic sibling, and never replaces an unsafe or stale destination. Codex cannot
use filesystem tools against the project because its working directory is an
isolated temporary context.

No dependency, unrelated refactor, secret, or public behavior outside the exact
`agent continue` vector was introduced.
