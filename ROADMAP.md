# Product roadmap

The platform is language-extensible. Java is the first target used to build
and validate the core workflow; it is not the only planned ecosystem.

## v0.1: Java and core workflow

- Project initialization and status.
- Maven and Gradle project detection.
- JUnit 5 detection and incremental test execution.
- Feature and bug sessions.
- Explicit human requirement review with approve/reject transitions.
- Typed design generation that stops for human design review.
- One-failing-test-at-a-time orchestration.
- Context isolation and state-machine recovery.

## v0.1.1: Agent provider and platform foundation

### Provider selection

- Add a typed Provider Registry while retaining single-provider execution for
  each workflow run.
- Provide `agent provider list`, `status`, `use`, `doctor`, and guarded
  installation commands.
- When an adapter-ready CLI is missing in an interactive terminal, ask before
  downloading the current stable CLI from its verified official source; never
  install during non-interactive selection or without explicit confirmation.
- Keep Codex as the first adapter-ready provider.
- Evaluate Claude Code, Cursor, and GitHub Copilot adapters only after verifying
  their current non-interactive CLI, structured-output, authentication, and
  licensing contracts.
- Keep a provider-neutral JSON command adapter for custom integrations.
- Require every provider adapter to pass the same typed contract, failure,
  timeout, redaction, and workflow-state tests.

### Linux Mint support

- Treat Linux Mint as a formally tested target rather than relying on assumed
  Python portability.
- Add `agent platform doctor` using the standard `os-release` contract to
  distinguish Linux Mint from compatible-but-untested Linux distributions.
- Diagnose Python version and private temporary-directory readiness without
  changing the host environment.
- Resolve provider executables from PATH or explicit configuration without
  silently installing tools or changing environment variables.
- Test Python 3.9, 3.10, and 3.12; Bash and Zsh; executable permissions;
  temporary paths; signals; timeouts; and child-process cleanup.
- Add CI coverage for Maven/Gradle and npm/pnpm/yarn workflows on Linux.
- Keep platform-specific executable fallbacks isolated behind typed resolvers.

## v0.2: TypeScript and Angular

### TypeScript foundation

- Detect TypeScript projects from project metadata and configuration files.
- Detect npm, pnpm, and yarn without assuming a package manager.
- Detect and invoke the project's configured Jest or Vitest commands.
- Generate typed SDD artifacts for TypeScript modules and public APIs.
- Apply the same incremental TDD loop used by Java: one failing test, minimal
  implementation, passing suite, refactor, repeat.

### Angular adapter

- Detect Angular workspaces and applications from their project metadata.
- Capture Angular architecture constraints in SDD design documents.
- Support incremental tests for components, services, directives, pipes,
  routing, forms, and HTTP integrations.
- Use the test runner and Angular testing facilities already configured by the
  target project instead of silently migrating its toolchain.
- Keep component templates, dependency injection, and asynchronous behavior
  visible in test plans and acceptance criteria.

## v0.3: Review, refactor, and observability

- Automated review and behavior-preserving refactoring stages.
- Quality metrics, test-loop metrics, cost, duration, and failure memory.
- Human approval gates and Git integration.

## v1.0: Model and ecosystem extensibility

- Multiple selectable code-agent adapters while retaining single-agent
  execution for each run.
- Project memory, plugin APIs, IDE integration, and additional languages and
  frameworks.
