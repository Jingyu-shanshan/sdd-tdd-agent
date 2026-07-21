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
- Typed incremental test plans now support component, service, directive, pipe,
  routing, form, and HTTP subjects with exact `.spec.ts` project-source-root
  boundaries and lossless one-current-test TDD parsing.
- Angular plans retain the configured runner and explicitly name the testing
  facilities they require instead of silently migrating the toolchain.
- Component templates, dependency injection, and asynchronous behavior are
  explicit typed fields in test plans and rendered acceptance evidence.
- Blind production collection, generation, atomic writes, GREEN verification,
  and final audit now use the current Angular test's exact verified project
  `sourceRoot`, including monorepo application/library roots, while preserving
  the legacy `src/**` boundary for other workflows.

## v0.3: Review, refactor, and observability

- Typed automated semantic review now covers Clean Code, SOLID, duplication,
  complexity, readability, bugs, performance, and security through isolated
  JSON/Codex adapters, exact source locations, deterministic reports, and an
  approved handoff to the existing integrity gate.
- One-file behavior-preserving refactoring now uses the approved semantic
  report, isolated JSON/Codex adapters, exact same-path replacement,
  digest-bound optimistic writes, the retained current/full-suite gates, and
  automatic source/state rollback on failed verification. The legacy
  no-source-change finalizer remains compatible.
- Privacy-safe append-only model/test telemetry now records Prompt identity,
  tool kind, outcomes, duration, and honest typed token/cost availability.
  `agent metrics` strictly aggregates active-Session call counts, success rate,
  duration, and verified usage without storing request, source, command, or
  output content.
- Exact task/test completion, build/test and refactor success, mean duration,
  and verified cost-per-feature projection now reuse validated plans, state,
  and telemetry. Bounded atomic cross-Session failure memory merges only
  content-free fingerprints and occurrence/Session counts; `agent metrics
  quality` and `agent failures` expose both views.
- Risk-bound human approval now canonicalizes exact path/kind changes, records
  low-risk exemption, and requires explicit digest-bound approval/rejection for
  medium/high-risk Git commits without storing source or diff content.
- Optional per-GREEN-cycle Git integration now prepares a scoped risk request,
  revalidates artifact/change digests, stages and commits only the exact current
  test/production paths, preserves unrelated staged changes, verifies HEAD, and
  archives source-free approval evidence. It never runs `git add .` or pushes.

## v1.0: Model and ecosystem extensibility

- Multiple selectable code-agent adapters while retaining single-agent
  execution for each run.
- Project memory, plugin APIs, IDE integration, and additional languages and
  frameworks.
