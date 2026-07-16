# Test plan

- Parse two rendered cases and select TC1.
- Select TC2 after TC1 completion; reject malformed/unknown progress.
- Reject wrong state, approvals, identity, missing/malformed artifacts.
- Start atomically and preserve completed IDs; reject duplicate active start.
- Prove Blind context exposes only current test, production, compile/test output.
- Run all quality, package, JSON, Git, commit, and push gates.
