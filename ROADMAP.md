# Product roadmap

The platform is language-extensible. Java is the first target used to build
and validate the core workflow; it is not the only planned ecosystem.

## v0.1: Java and core workflow

- Project initialization and status.
- Maven and Gradle project detection.
- JUnit 5 detection and incremental test execution.
- Feature and bug sessions.
- One-failing-test-at-a-time orchestration.
- Context isolation and state-machine recovery.

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

- Multiple code-agent adapters while retaining single-agent execution.
- Project memory, plugin APIs, IDE integration, and additional languages and
  frameworks.

