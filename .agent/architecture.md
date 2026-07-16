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
- Isolate requirement-analysis models behind an injected typed Protocol. Load
  versioned Prompts from packaged files, validate all structured output before
  mutation, and require human review before DESIGN.
- Keep requirement review deterministic and model-free. Load only the active
  validated Session, require explicit approval or a reasoned rejection, record
  the decision in state, and atomically transition to DESIGN or back to
  ANALYSIS.
- Isolate design generation behind its own injected typed Protocol and
  versioned Prompt. Require both DESIGN state and the stored human requirement
  approval, validate structured design output before mutation, and stop at
  DESIGN_REVIEW rather than silently entering task breakdown.
- Implement design model integration in a separate adapter module. Reuse the
  existing tokenized process/configuration/resolver contracts, enforce the exact
  ten-field JSON Schema, and apply the same ephemeral read-only Codex exchange
  without mixing Session mutation into provider code.
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
  IMPLEMENTATION without writing or running test code.
- Implement test-plan model integration in a separate adapter module. Decode
  exact nested case objects through provider-neutral JSON or the existing
  ephemeral read-only Codex exchange, reuse injected process/resolver contracts,
  and leave semantic ordering and Session mutation in the workflow.
- Compose `agent tests` through a dedicated active-Session service that selects
  the configured test-plan adapter and delegates approvals, semantics, and
  artifact/state mutation to the core workflow.
- Parse only deterministic generated test plans when entering implementation.
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
- Do not add Typer, Pydantic, SQLite, LangGraph, or other dependencies before a
  concrete behavior needs them and a human approves the dependency.
