# Requirement

## User request

Prove the complete implemented SDD and incremental TDD workflow from project
initialization and feature creation through DONE.

## Requirements

- Drive only public CLI behavior in a fresh temporary TypeScript/Vitest project.
- Exercise requirement analysis and approval, design generation and approval,
  task generation and approval, and test-plan generation.
- Exercise one complete WRITE_TEST -> RED -> IMPLEMENT -> GREEN cycle.
- Exercise exhausted-plan completion, deterministic review, final refactor
  verification, and DONE.
- Use injected typed model and test runners; execute no real model, package
  manager, network request, or host mutation.
- Assert exact state ordering, command ordering, configured timeout separation,
  context isolation, final audit records, and deterministic CLI output.
- Keep the real active user Session and unrelated repository files unchanged.

## Out of scope

- A non-interactive command that bypasses human approval gates.
- Real provider or target-project process execution.
- Multi-test retry/recovery scenarios already covered by focused tests.
- Release, deployment, or pull-request automation.
