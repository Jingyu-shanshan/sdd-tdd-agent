# Product roadmap

The platform is language-extensible. Java is the first target used to build
and validate the core workflow; it is not the only planned ecosystem.

## v0.1: Java and core workflow

- Project initialization and status.
- Maven and Gradle project detection.
- JUnit 5 detection and incremental test execution.
- Feature and bug Sessions with shared safe creation, activation, and downstream
  workflow compatibility.
- Explicit human requirement review with approve/reject transitions.
- Typed design generation with JSON/Codex adapters that stops for human design
  review.
- Active-Session `agent design` orchestration through the selected Provider.
- Explicit human design review with approve/reject transitions before task
  breakdown.
- Typed ordered task breakdown with dependency, acceptance, and test-target
  validation that stops at task review.
- Strict JSON command and ephemeral read-only Codex task-breakdown adapters with
  nested task Schema validation.
- Active-Session `agent tasks` orchestration through the selected Provider that
  stops at task review.
- Explicit human task review with show/approve/reject transitions before test
  generation.
- Typed incremental test-plan generation with ordered phases, task coverage,
  preceding-test dependencies, and safe target-path validation.
- Strict JSON command and ephemeral read-only Codex test-plan adapters with
  nested case Schema validation.
- Active-Session `agent tests` orchestration through the selected Provider.
- One-test-at-a-time cycle selection and a typed Blind development context.
- Isolated one-test source generation with strict JSON and Codex adapters.
- Safe active-Session test-source writing through the first `agent continue`
  IMPLEMENTATION slice.
- Shell-free one-test command planning for Maven/Gradle/JUnit 5 and
  npm/pnpm/yarn with Jest, Vitest, or Angular CLI.
- Digest-bound, shell-free one-failing-test-at-a-time RED execution with
  attributable failure checks, sanitized bounded evidence, and recoverable
  state transitions.
- Minimal one-file production-code generation through isolated Blind JSON/Codex
  adapters, strict `src/**` policy, optimistic atomic writing, and RED to
  IMPLEMENT state evidence.
- Digest-bound GREEN verification and shell-free full-suite regression checks
  with separate timeouts, sanitized evidence, and safe RED recovery.
- Ordered GREEN cycle advancement and trustworthy exhausted-plan transition to
  REVIEW.
- Deterministic digest-bound implementation audit report and REVIEW to REFACTOR
  transition.
- Deterministic no-source-change refactor verification with current-test and
  full-suite gates, immutable audit-chain checks, and atomic REFACTOR to DONE.
- Full public-CLI acceptance coverage from initialization through DONE with
  injected model/test runners and explicit human approval gates.
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
- Run the quality suite automatically on explicit Ubuntu 24.04 workers with
  Python 3.9, 3.10, and 3.12, plus Bash and Zsh test entry points.
- Provide a manual, label-constrained workflow for a real Linux Mint
  self-hosted runner. The target remains pending real-host validation until
  that workflow records a successful run.
- Keep executable-permission, temporary-path, signal, timeout, and child-process
  contracts in the Linux-hosted suite and expand them with real-host failures as
  evidence becomes available.
- Run existing Maven/Gradle and npm/pnpm/yarn planning contracts on Linux and
  execute locked minimal JUnit/Vitest fixture projects through all five real
  toolchains on Ubuntu CI.
- Keep platform-specific executable fallbacks isolated behind typed resolvers.

## v0.2: TypeScript and Angular

### TypeScript foundation

- Root package-manager and Jest/Vitest test-command detection plus generic
  digest-bound RED execution and Blind minimal production-source orchestration
  are implemented. Design generation now carries verified TypeScript project
  context with a supported root `tsconfig` marker into a dedicated versioned
  Prompt and produces validated module and public-API SDD sections.
- TypeScript project, npm/pnpm/yarn, and Jest/Vitest detection are implemented
  from explicit project metadata and configuration evidence.
- Typed SDD artifacts for safe TypeScript modules and public APIs are
  implemented without changing generic or Java design contracts.
- Apply the same incremental TDD loop used by Java: one failing test, minimal
  implementation, passing suite, refactor, repeat.

### Angular adapter

- Root Angular workspace detection, exact non-watch file/name command planning,
  generic RED execution, and Blind `src/**` production generation are
  implemented. Design generation now strictly carries configured application/
  library boundaries into a dedicated Angular Prompt and requires typed,
  verifiable architecture constraints.
- Angular workspaces, applications, and libraries are detected from explicit
  package and `angular.json` metadata.
- Typed Angular architecture constraints and project-source-root boundaries are
  captured in deterministic SDD design documents.
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
