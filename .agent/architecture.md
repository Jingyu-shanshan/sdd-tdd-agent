# Architecture

## Context

The product is a CLI platform that coordinates a single code agent through
multiple isolated contexts. Python implements the platform; Java is the first
target project language supported by the MVP. TypeScript and Angular follow
after the core workflow is proven and reuse the same SDD artifacts, state
machine, context isolation, and incremental TDD loop.

## Initial architecture

The platform starts as a single Python package with a thin CLI boundary. The
`project_init` module owns workspace filesystem changes independently of CLI
dispatch. The side-effect-free `project_detection` module maps root-level
project markers and Maven dependency metadata to an immutable project profile.
New workflow behavior will be introduced behind application-layer interfaces
only when a failing acceptance test requires it.

## Decisions

- Use the Python standard library for the bootstrap increment.
- Expose the executable as `agent` and the module as `sdd_tdd_agent`.
- Keep CLI parsing separate from command behavior so output can be unit tested.
- Create bootstrap metadata with exclusive first-write semantics so repeated
  initialization preserves project knowledge.
- Keep project detection read-only and separate from metadata persistence.
- Parse valid Maven POM files with the standard library and match XML local
  names so standard namespace versions do not leak into domain rules.
- Keep project/session status loading and deterministic text rendering outside
  CLI dispatch. Validate session identifiers before resolving state paths.
- Create feature sessions exclusively with immutable typed results, pending SDD
  templates, safe generated IDs, and atomic active-session metadata updates.
- Create bug Sessions through the same internal Session-creation service and
  standard eight-artifact contract while exposing a distinct typed result and
  `agent bug` entry point. Downstream workflows remain kind-neutral and retain
  the recorded `feature` or `bug` kind.
- Isolate requirement-analysis models behind an injected typed Protocol. Load
  versioned Prompts from packaged files, validate all structured output before
  mutation, and require human review before DESIGN.
- Keep requirement review deterministic and model-free. Load only the active
  validated Session, require explicit approval or a reasoned rejection, record
  the decision in state, and atomically transition to DESIGN or back to
  ANALYSIS.
- Isolate design generation behind its own injected typed Protocol and
  versioned Prompt. Select dedicated TypeScript or Angular Prompts only from
  verified project detection with a supported root `tsconfig` marker, carry
  immutable package-manager/framework/config evidence, and keep projects
  without that evidence plus generic and Java requests on v1. For Angular,
  strictly load `angular.json` workspace version and application/library
  boundaries before generation. Require both DESIGN state and the stored human
  requirement approval, validate structured design output before mutation, and
  stop at DESIGN_REVIEW rather than silently entering task breakdown.
- Implement design model integration in a separate adapter module. Reuse the
  existing tokenized process/configuration/resolver contracts, enforce the ten
  required generic JSON fields plus optional strict TypeScript module/public-API
  and Angular architecture-constraint records, and apply the same ephemeral
  read-only Codex exchange without mixing Session mutation into provider code.
  TypeScript workflows require normalized source modules, non-empty exports,
  closed API kinds, unique identities, and valid module references. Angular
  modules must stay under a configured project source root, and constraint
  areas, content, and uniqueness are validated before artifact mutation.
- Parse Angular workspace metadata in a separate read-only module with strict
  JSON duplicate-key handling. Accept only configured application/library
  records with normalized project and source-root boundaries; do not resolve or
  infer builders, configurations, or runtime conventions.
- Compose `agent design` through a dedicated active-Session service that reuses
  the selected Provider protocol, command, and timeout, chooses the matching
  design adapter, and delegates all state/artifact validation to the design
  workflow.
- Keep design review model-free and explicit. Require DESIGN_REVIEW plus the
  persisted requirement approval, atomically record approve/reject decisions,
  and transition only to TASK_BREAKDOWN or back to DESIGN.
- Generate task breakdowns behind an injected typed Protocol and versioned
  Prompt. Require both human approvals, enforce unique stable IDs and only
  preceding-task dependencies, validate acceptance/test targets before
  mutation, and stop at TASK_REVIEW.
- Implement task-breakdown model integration in a separate adapter module.
  Decode exact nested task objects through either provider-neutral JSON or the
  existing ephemeral read-only Codex exchange, reuse injected process and
  resolver contracts, and leave Session mutation and semantic dependency
  validation in the task workflow.
- Compose `agent tasks` through a dedicated active-Session service that reuses
  strict tracked configuration, selects the matching task adapter, and delegates
  both approvals, state validation, task semantics, and artifact mutation to the
  task-breakdown workflow.
- Keep task review deterministic, model-free, and explicit. Require TASK_REVIEW
  plus both persisted approvals, validate generated task content, atomically
  record approve/reject decisions, and transition only to TEST_GENERATION or
  back to TASK_BREAKDOWN.
- Generate test plans behind an injected typed Protocol and versioned Prompt.
  Require all three human approvals, cover every approved task, enforce the
  happy/boundary/exception/integration/regression order and only preceding-test
  dependencies, validate relative target paths before mutation, and enter
  IMPLEMENTATION without writing or running test code. For verified Angular
  projects, select a dedicated Prompt, carry strict workspace boundaries, and
  require every case to identify its configured project, supported subject,
  testing facilities, template contracts, dependency-injection behavior, and
  asynchronous behavior. Constrain Angular cases to exact `.spec.ts` paths
  below their project source root.
- Implement test-plan model integration in a separate adapter module. Decode
  exact nested case objects through provider-neutral JSON or the existing
  ephemeral read-only Codex exchange, reuse injected process/resolver contracts,
  and leave semantic ordering and Session mutation in the workflow.
- Compose `agent tests` through a dedicated active-Session service that selects
  the configured test-plan adapter and delegates approvals, semantics, and
  artifact/state mutation to the core workflow.
- Parse only deterministic generated test plans when entering implementation.
  Accept either the exact legacy section set or the exact Angular extension,
  reconstruct typed Angular metadata, and re-run contextual plan validation.
  Track an ordered completed-test prefix and one current cycle in Session state;
  keep the developer context restricted to the current test, production source,
  and compiler/test output.
- Generate one test source behind a separate typed Test Context. Supply only the
  approved requirement/design, current test case, and explicit safe source
  snapshots; exclude tasks, the complete plan, future tests, and execution
  output. Bind strict JSON/Codex results to the current test ID and planned file
  without letting the read-only model exchange mutate the project.
- Compose the IMPLEMENTATION slice of `agent continue` from recoverable cycle
  preparation, bounded workspace source collection, the selected test-source
  adapter, and an optimistic-concurrency atomic writer. Run Codex from a
  project-external temporary directory so its read-only tools cannot bypass the
  typed Test Context. Leave the cycle in WRITE_TEST until RED is independently
  observed.
- Plan one-test execution through a read-only cross-ecosystem detector. Share
  strict Node metadata between project classification and command construction;
  require explicit package-manager/framework evidence, use tokenized Maven/
  Gradle/Jest/Vitest/Angular filters, and escape/anchor regex-based Node test
  names so one cycle cannot accidentally run additional tests.
- Bind an atomically written current test to its ID, planned relative path, and
  SHA-256 digest before execution. On the next `agent continue`, revalidate the
  digest before and after a shell-free injected one-test runner, and enter RED
  only for a positive non-zero failure attributable to that test. Keep pass,
  signal, timeout, command/configuration, no-test, unrelated-output, and
  concurrent-change outcomes recoverable in WRITE_TEST. Persist only sanitized,
  bounded stdout/stderr and the exact tokenized command in Session state.
- Generate minimal production code behind a separate Blind typed boundary that
  receives only the digest-bound current test plan/source, visible production
  snapshots, sanitized stderr as compile output, and sanitized stdout as test
  output. Run Codex from an ephemeral project-external directory and require an
  exact one-file result. Restrict writes to normalized non-test `src/**` source,
  use optimistic-concurrency atomic replacement, and record only ID/path/digest
  while transitioning RED to IMPLEMENT. Never expose SDD documents, the full
  plan, future tests, configuration, raw Session state, or direct project tool
  access to the Blind model.
- Verify IMPLEMENT through two deterministic shell-free gates: the exact
  digest-bound current test and then an unfiltered full suite with a separate
  required timeout. Revalidate test, production, and Session state around both
  processes. Only two zero exits append the current test and enter GREEN;
  attributable current or regression failures return to RED with sanitized
  retry evidence, while infrastructure and concurrency failures preserve
  IMPLEMENT. This stage never invokes a model.
- Advance GREEN deterministically from the ordered completed prefix. If a test
  remains, clear every prior-cycle artifact and reuse isolated test-source
  generation for exactly that next case. If the plan is exhausted, revalidate
  final test/production digests and exact sanitized GREEN process evidence,
  then atomically enter REVIEW with no model or process execution.
- Bind REVIEW to a canonical implementation-completion snapshot. `agent review`
  validates that snapshot against retained TDD evidence and artifact records,
  writes a deterministic source/output-free audit report, records its digest,
  and enters REFACTOR without external execution. State clearly that semantic
  automated code review remains a later milestone.
- Complete v0.1 REFACTOR without claiming automated source improvement.
  `agent refactor` validates the complete report/completion/GREEN/source digest
  chain around each process, reruns the exact current test followed by the
  unfiltered suite under separate timeouts, stores only sanitized bounded
  evidence, and atomically enters DONE after two zero exits. It invokes no model
  and writes no source; behavior-preserving automated refactoring remains v0.3.
- Prove the integrated core with a public-CLI acceptance test in a fresh
  detected project. All model and target-process effects stay behind injected
  typed runners, so the test exercises every human gate and state transition
  from initialization through DONE without network, package-manager, or host
  execution. Keep ecosystem-specific failure depth in focused contract tests.
- Support provider-neutral model bridges through a strict JSON stdin/stdout
  adapter and an injected process runner. Production execution must use
  tokenized arguments with `shell=False` and redact process/request content from
  errors.
- Compose `agent analyze` from strict tracked configuration, active Session
  resolution, the JSON adapter, and the analysis workflow. Require JSON-string
  command tokens and an explicit finite timeout; never infer executable or
  credentials from hidden state.
- Integrate Codex through an explicit `codex-exec` protocol on the same typed
  adapter boundary. Use the configured executable and timeout, ephemeral
  read-only execution, a strict output Schema, and operating-system temporary
  exchange files. Preserve `json-command` as the provider-neutral default.
- Resolve the standard `codex` command from PATH first. On macOS only, fall back
  to the executable bundled with the installed ChatGPT application when PATH
  lookup fails; keep custom executable names untouched.
- Represent supported and planned agents in a typed Provider Registry. Provider
  selection is explicit and persisted in tracked configuration, while each run
  still executes exactly one provider. Planned providers must not be selectable
  until their CLI and structured-output contracts are implemented and tested.
- Treat Linux Mint as a formal target platform. Keep platform discovery behind
  injected resolvers, prefer PATH or explicit configuration, and validate
  subprocess, permission, temporary-file, signal, and toolchain behavior in a
  Linux CI matrix.
- Keep real multi-toolchain acceptance fixtures isolated under test data. Their
  Maven, Gradle, npm, pnpm, and Yarn metadata must be accepted by the same
  production detectors and their CI commands must match production plans.
- Model host detection as an injected read-only Platform Environment. On Linux,
  parse only standard `os-release` identifiers, reject malformed/duplicate
  fields, and classify `ID=linuxmint` as the formal target while reporting other
  Linux distributions as compatible but untested. Diagnose Python and temporary
  directory readiness independently from platform identity.
- Diagnose and install provider CLIs behind typed, injected locator and process
  boundaries. Installation is allowed only for adapter-ready providers with a
  verified official plan and explicit interactive confirmation. Download and
  execution are separate tokenized `shell=False` processes; successful install
  must be followed by executable and version verification before selection.
- Resolve Blind production write permissions from the typed current test. Keep
  generic workflows at `src/**`; for Angular, map the current case's project to
  its strictly parsed configured `sourceRoot` and expose only that normalized
  boundary through a dedicated versioned Prompt. Apply the same root to source
  collection, result validation, optimistic atomic writes, GREEN digest checks,
  and final REFACTOR audit. Persist a `source_root` only for non-default Angular
  artifacts so legacy three-field records and provider payloads remain exact.
- Add semantic implementation review as an explicit REVIEW substage before the
  deterministic integrity transition. Revalidate completion and final source
  digests, then expose only the final test/production snapshots and completion
  identity through a versioned Prompt and strict injected JSON/Codex reviewer.
  Validate closed review areas/severities, exact visible paths and line numbers,
  decision consistency, bounded text, source-copy rejection, and duplicates
  before atomically recording a source-free report. Keep required changes in
  REVIEW; only an approved digest-bound semantic record may be preserved by
  `agent review` while entering REFACTOR. Retain the invariant-only legacy path.
- Add one-file behavior-preserving refactoring only after the approved semantic
  path. Reuse the final audit-chain loader, test commands, evidence sanitizer,
  Provider configuration, and process runners. Expose only the approved
  source-free report, completion/review digests, and exact production source
  through a versioned Prompt and strict JSON/Codex Schema. Require a changed
  same-path result, atomically bind before/after digests, reuse both final test
  gates, and restore source/state on failure. Keep invariant-only Sessions on
  the existing no-source-change path.
- Observe workflow model/test calls by decorating the two existing injected
  runner interfaces at CLI composition. Append only bounded allowlisted events
  under `.agent/metrics`: operation, kind, sanitized tool, outcome, duration,
  and Prompt version/digest. Never persist request/output/argument content.
  Keep token/cost fields typed but unavailable until a verified Provider
  contract supplies them; never estimate billing. Strictly aggregate active-
  Session call counts, rates, duration, and complete reported usage through
  `agent metrics`.
- Do not add Typer, Pydantic, SQLite, LangGraph, or other dependencies before a
  concrete behavior needs them and a human approves the dependency.
