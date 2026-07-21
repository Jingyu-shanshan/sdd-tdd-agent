# Test Plan

- Documentation/test-only modifications classify low without human approval.
- Production modifications classify medium and require approval.
- Deletions and control/dependency changes classify high.
- Equivalent unordered change sets produce one deterministic digest.
- Unsafe paths, duplicate paths, invalid kinds, and empty sets fail.
- Request creation is exact and idempotent only for the same request.
- Approve/reject operations bind to the active pending digest.
- Tampered, symlinked, stale, and colliding records fail without mutation.
- CLI status and decisions are deterministic and source-free.
