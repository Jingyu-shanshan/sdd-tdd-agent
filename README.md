# sdd-tdd-agent

A CLI platform for software-design-driven development (SDD) and incremental
test-driven development (TDD), built around a single agent with isolated
contexts.

## Current capabilities

The current v0.1 core provides a working public CLI from project/session setup
through requirement, design, task, and test-plan approval gates; isolated
incremental TDD implementation; deterministic review; final verification; and
DONE. Model and target-process boundaries remain typed, injected, and testable.

```bash
uv run agent hello
```

Expected output:

```text
Hello, World!
```

Initialize the current project's agent workspace with:

```bash
uv run agent init
```

The command creates `.agent/` metadata plus the `memories`, `sessions`,
`cache`, `logs`, and `metrics` directories. Re-running it preserves existing
metadata. Fresh workspaces also record Java/Maven projects detected by
`pom.xml` and Java/Gradle projects detected by `build.gradle` or
`build.gradle.kts`. Maven projects declaring an `org.junit.jupiter` dependency
also record JUnit 5 as their test framework. Root TypeScript projects are
detected from strict `package.json` metadata plus an explicit `packageManager`
or one consistent lockfile; configured Jest, Vitest, and Angular test scripts
are reported without guessing a package manager or framework. Fresh metadata
also records configured Maven or Gradle Checkstyle, SpotBugs, and PMD tools,
plus Node ESLint and Prettier tools when both dependency and script evidence is
present. Discovery is read-only and never installs or runs those tools.

The tracked `project.yml`, `architecture.md`, and `conventions.md` files are the
canonical cross-Session project memory. Inspect its validated snapshot identity
without printing its content:

```bash
uv run agent memory
```

The loader rejects missing, empty, unsafe, invalid UTF-8, concurrently changed,
or over-1-MB combined memory. Requirement analysis consumes this same coherent
typed snapshot; no database, embedding store, or second mutable copy is used.

Inspect project classification and the active development session with:

```bash
uv run agent status
```

Start a feature SDD session with:

```bash
uv run agent feature "Support PDF export"
```

The command records the request, creates the eight standard session artifacts,
sets the workflow state to `ANALYSIS`, and activates the new Session.

Start a bug-fix SDD session through the same workflow with:

```bash
uv run agent bug "Fix empty PDF export"
```

The bug command applies the same normalization, safe unique-ID, exclusive
creation, complete artifact, and atomic activation contract, while recording
`kind: bug`. Invalid or colliding input cannot replace the active Session.
After creation, use the same `analyze`, explicit review, design, task, test, and
incremental implementation commands as a feature Session.

The requirement-analysis core provides a typed, dependency-injected
`RequirementAnalyzer` boundary. It loads the versioned Prompt and project
context, validates structured output, writes reviewable requirements, and stops
at `REQUIREMENT_REVIEW`.

The model boundary sends typed analysis requests through stdin, accepts strict
JSON results, and executes already-tokenized commands without a shell. The
repository is configured for the built-in Codex CLI protocol:

```yaml
requirement_analyzer_protocol: codex-exec
requirement_analyzer_command:
  - "codex"
requirement_analyzer_timeout_seconds: 300
test_command_timeout_seconds: 300
```

The Codex executable must already be authenticated. The bridge resolves `codex`
from `PATH`; on macOS it also supports the executable bundled with the ChatGPT
application when a terminal does not inherit the app's PATH. Custom executable
names are never redirected. The bridge runs `codex exec` ephemerally with a
read-only sandbox and strict output Schema; it does not override the user's
model selection or store credentials in project configuration. Analyze the
active Session with:

```bash
uv run agent analyze
```

Successful analysis stops at `REQUIREMENT_REVIEW` for human confirmation.
Inspect the active analyzed requirement and make the explicit human decision
with:

```bash
uv run agent requirement show
uv run agent requirement approve
uv run agent requirement reject "Clarify the expected output"
```

Approval records the decision and advances the Session to `DESIGN`. Rejection
requires a reason, records it, and returns the Session to `ANALYSIS`. These
commands do not invoke a model. Invalid states fail without changing the
Session.

The design-generation core is also available behind an injected, typed
`DesignGenerator` boundary. It accepts only a Session in `DESIGN` with a stored
human approval record, loads the versioned design Prompt and tracked project
context, validates a structured proposal, writes deterministic `design.md`, and
stops at `DESIGN_REVIEW`. Strict provider-neutral JSON command and Codex exec
adapters implement this boundary. Codex design runs use the same ephemeral,
read-only, shell-free, strict-Schema exchange as requirement analysis. CLI
orchestration uses the currently selected Provider configuration. After
explicitly approving a requirement, generate the active Session design with:

```bash
uv run agent design
```

Detected TypeScript projects with a supported root `tsconfig` marker use the
dedicated versioned `v2-typescript` Prompt. Their typed request context records
the verified package manager, test framework, Angular classification, and root
TypeScript configuration markers. The proposal adds strictly validated
`src/**/*.ts` or `src/**/*.tsx` module records and their public APIs, and
renders them as deterministic SDD sections. Projects without that explicit
configuration evidence, plus generic and Java projects, retain the original v1
request and output contract.

Verified Angular projects with a supported root `tsconfig` use the dedicated
`v3-angular` Prompt. The read-only context strictly loads the workspace version
and each configured application/library boundary from `angular.json`. Proposed
modules must remain under one configured project `sourceRoot`, including
monorepo library roots. Typed architecture constraints record an allowed area,
decision, rationale, and verification method before the design can enter human
review.

The command requires `DESIGN` state and the stored human approval record. A
valid structured result writes `design.md` and stops at `DESIGN_REVIEW`; invalid
configuration, state, or model output fails without advancing the Session.

Inspect and make the explicit human design decision with:

```bash
uv run agent design show
uv run agent design approve
uv run agent design reject "Clarify the component boundary"
```

Approval records the decision and enters `TASK_BREAKDOWN`. Rejection requires a
reason, records it, and returns to `DESIGN`. These review commands do not invoke
a model or process runner.

The task-breakdown core accepts only `TASK_BREAKDOWN` Sessions with stored
requirement and design approvals. Through an injected typed generator it creates
ordered tasks with stable IDs, preceding-task dependencies, affected areas,
acceptance criteria, and test targets. Valid output writes deterministic
`tasks.md` and stops at `TASK_REVIEW`. Strict provider-neutral JSON command and
Codex exec adapters implement the generator boundary with exact nested task
Schemas, ephemeral read-only execution, temporary exchange cleanup, and safe
errors. After explicitly approving the design, generate tasks for the active
Session through the currently configured Provider with:

```bash
uv run agent tasks
```

The command requires `TASK_BREAKDOWN` state and both stored human approvals. A
valid structured result writes `tasks.md` and stops at `TASK_REVIEW`; invalid
configuration, state, or model output fails without advancing the Session.

Inspect and make the explicit human task decision with:

```bash
uv run agent tasks show
uv run agent tasks approve
uv run agent tasks reject "Split the CLI task"
```

Approval records the decision and enters `TEST_GENERATION`. Rejection requires a
reason, records it, and returns to `TASK_BREAKDOWN`. These review commands do not
invoke a model or process runner, and invalid review input does not mutate the
Session.

The test-generation core accepts only `TEST_GENERATION` Sessions with all three
stored human approvals. Through an injected typed generator it plans ordered,
independently executable tests across happy-path, boundary, exception,
integration, and regression phases. It enforces stable test/task IDs,
preceding-test dependencies, complete task coverage, and safe relative target
paths. Valid output writes deterministic `test-plan.md` and enters
`IMPLEMENTATION`; it does not write or run test code. Strict provider-neutral
JSON command and Codex exec adapters implement this generator boundary with an
exact nested case Schema, ephemeral read-only execution, private temporary
exchange cleanup, and safe errors. CLI orchestration remains deferred to the
next increment. Generate the active Session plan through the currently selected
Provider with:

```bash
uv run agent tests
```

Detected Angular projects use the dedicated `v2-angular` test Prompt and strict
workspace context. Every planned case identifies its configured Angular
project and one supported component, service, directive, pipe, routing, form,
or HTTP subject. Testing facilities, template contracts, dependency-injection
behavior, and asynchronous behavior remain explicit in both typed JSON and
rendered Markdown. Each `.spec.ts` path must remain under that project's
configured `sourceRoot`, and the implementation-cycle parser restores the same
typed metadata before selecting exactly one current test.

The command requires `TEST_GENERATION` plus all three approvals. Valid output
writes `test-plan.md` and enters `IMPLEMENTATION`; configuration, state, or model
failure does not advance the Session.

The implementation-cycle core then selects exactly one incomplete test in plan
order and atomically records `WRITE_TEST` progress. Completed tests must form a
plan prefix and all dependencies must already be GREEN. Its typed Blind
development context exposes only the current test, explicitly supplied
test source, production snapshots, and compile/test output—never requirements,
design, tasks, the complete plan, or future tests.

The single-test generation core uses a separate Test Context: it may see the
approved requirement/design, exactly one current test case, and explicitly
supplied safe source snapshots. It cannot see tasks, the complete test plan,
future tests, or compiler/test output. A versioned Prompt and typed generator
produce one complete test file; strict JSON command and ephemeral read-only
Codex adapters require the result to match the current test ID and its planned
relative path. Continue the active IMPLEMENTATION Session with:

```bash
uv run agent continue
```

On the first invocation for a cycle, the command resumes or starts exactly one
`WRITE_TEST` cycle, collects bounded current source/config snapshots, invokes
the selected Provider, and atomically writes only the planned test file.
Existing targets use optimistic concurrency checks; unsafe paths, symbolic
links, stale snapshots, and temporary collisions fail before replacement.
Codex runs from a project-external temporary directory so read-only tool access
cannot inspect `.agent` or future tests. The resulting file ID, relative path,
and SHA-256 digest are recorded while the cycle remains in `WRITE_TEST`.

On the second invocation, `agent continue` verifies the recorded digest and
executes exactly that current test from the project root. The shell-free runner
uses the separately configured positive finite `test_command_timeout_seconds`.
It records RED only for a positive non-zero exit whose output identifies the
current test. Unexpected passes, signals, timeouts, startup failures, no-test or
bad-option diagnostics, unrelated output, and files changed before or during
execution preserve `WRITE_TEST` and return a safe error. Stored stdout/stderr
have ANSI/control data, project-root paths, and common credentials removed and
are length-bounded. A successful RED transition reports, for example:

```text
RED confirmed: feature-1 (TC1, exit 1)
```

On the third invocation, `agent continue` builds the Blind development context
from that digest-bound current test, visible production source, and sanitized
RED stderr/stdout (mapped to compile/test output). The selected Provider must
return the complete content of exactly one minimal production file. Strict JSON
and isolated ephemeral read-only Codex adapters never receive requirement,
design, task, complete-plan, future-test, or raw Session content.

The writer permits only normalized supported source files below the current
verified production root. Generic, Java, and root TypeScript projects retain
the exact `src/**` boundary. Angular cases resolve their owning application or
library from strict `angular.json` metadata and may write only below that
project's configured `sourceRoot`, including monorepo roots such as
`projects/shared/src/**`; sibling projects remain inaccessible. The Blind
Angular provider sees only this normalized writable root, never workspace
metadata. Test-like paths, configuration/build files, hidden paths, traversal,
symbolic links, stale targets, invalid UTF-8, and temporary collisions are
rejected. Existing source is replaced only if its captured content is
unchanged; one safe new source may be created. Success atomically records the
production file ID, path, SHA-256, and any non-default Angular root, then
advances only RED to IMPLEMENT:

```text
Production source ready for GREEN: feature-1 (TC1 -> src/export.ts)
```

On the fourth invocation, `agent continue` revalidates both recorded source
digests, runs the exact current test first, and runs the complete suite only
after that test passes. The suite uses its own required positive finite
`full_test_suite_timeout_seconds`. Maven and Gradle run their unfiltered test
tasks; Jest, Vitest, and Angular use non-watch full-suite arguments through the
verified package-manager prefix.

Only two zero exits atomically append the current test to the completed plan
prefix and advance IMPLEMENT to GREEN:

```text
GREEN confirmed: feature-1 (TC1; current test and full suite passed)
```

A trustworthy current-test failure or full-suite regression returns the cycle
to RED with sanitized bounded retry evidence. Signals, timeouts, startup
failures, no-test or invalid-option diagnostics, empty failures, changed
sources, and concurrent state updates preserve IMPLEMENT. GREEN verification
is deterministic, invokes no model, and never treats production-source writing
alone as proof that tests pass.

On the next invocation after GREEN, `agent continue` checks the ordered plan.
If another dependency-ready test remains, it clears all prior-cycle evidence
and starts exactly that test through the same isolated WRITE_TEST generation
path. If the completed prefix exhausts the plan, it revalidates both final
source digests and the exact sanitized current/full-suite GREEN evidence, then
atomically enters REVIEW without invoking a model or process runner:

```text
Implementation ready for review: feature-1 (1 tests GREEN)
```

Stale artifacts, incomplete plans, malformed evidence, concurrent state
changes, or atomic collisions preserve GREEN for safe recovery.

After the exhausted plan enters REVIEW, an explicit semantic review can inspect
only the digest-bound final test and production source through the selected
Provider:

```bash
uv run agent review semantic
```

The versioned semantic Prompt and strict JSON/Codex adapters classify concrete
findings across Clean Code, SOLID, duplication, complexity, readability,
potential bugs, performance, and security. Every finding has a stable ID,
closed severity, exact visible path, valid one-based line, message, and
recommendation. Codex runs from a project-external ephemeral read-only exchange;
the model never receives requirements, design, tasks, process output, raw state,
credentials, or unrestricted repository access. Outputs that copy source or
look like credentials are rejected.

The command writes a deterministic source-free `review.md` plus a completion-
and-report-digest-bound state record, but intentionally remains in REVIEW.
`changes_required` findings block progression; an approved review is still
subject to the deterministic integrity audit. Projects that do not request the
semantic step retain the compatible invariant-only path.

Run the deterministic implementation audit after the optional semantic review:

```bash
uv run agent review
```

The command verifies the digest-bound completion snapshot against the retained
completed-test prefix, final test, GREEN evidence, and test/production artifact
records. It writes a bounded `review.md` containing IDs, counts, and digests—no
source or process output—then atomically enters REFACTOR. It invokes no model,
test runner, or shell command. Without a semantic report, its legacy report
explicitly states that semantic findings were not computed. With an approved
semantic record, it preserves that report and records `semantic_review_passed`
before entering REFACTOR.

Finish with either automated source refactoring or the compatible no-source
verification path:

```bash
uv run agent refactor automated
uv run agent refactor
```

`agent refactor automated` requires the approved semantic-review path. Through
the selected JSON/Codex Provider it exposes only the versioned Prompt, approved
source-free report, completion/review digests, and exact final production file.
The result must be a changed same-path complete source. It is written with a
digest-bound optimistic record, then the existing current-test and full-suite
gates run. Both must pass before DONE; either failure restores the captured
source and REFACTOR state. Codex uses a project-external ephemeral read-only
exchange, and provider errors never include source or review payloads.

Plain `agent refactor` retains the v0.1 no-source-change behavior and invokes no
model. Both paths revalidate the complete review, completion, GREEN-evidence,
and final-source audit chain around the two test processes, store only sanitized
bounded final evidence, and enter DONE atomically. Unbound source changes,
failed processes, stale state, unsafe paths, or concurrent updates fail safely.

For Angular monorepos, GREEN, completion, review, and final REFACTOR
verification retain and revalidate the exact recorded source-root boundary as
well as the digest. Changing the artifact path or widening it to another
configured Angular project invalidates the audit chain.

Workflow model and test calls produce privacy-safe active-Session telemetry:

```bash
uv run agent metrics
```

The CLI decorates the existing injected runners, so adapters and workflow logic
remain unchanged. Each bounded append-only event records the operation, model or
test kind, sanitized executable name, success/return code, duration, and only a
Prompt version plus SHA-256 identity. It never stores Prompt/source/review text,
command arguments, stdout, stderr, credentials, or personal data. Current
Provider protocols do not expose verified token or billing data, so token and
cost values are explicitly reported as unavailable rather than estimated.
Strict aggregation reports call counts, success rate, total duration, and usage
when a future verified Provider supplies it. Runtime files remain below the
ignored `.agent/metrics/` directory.

Quality projection and durable failure memory build on that telemetry without
storing private content:

```bash
uv run agent metrics quality
uv run agent failures
```

Quality metrics reuse the validated test-plan parser and trusted completed-test
prefix to calculate exact task/test completion rates. They combine validated
test/refactor events for success rates and mean duration; cost per feature stays
unavailable unless every event contains verified Provider usage. Failed events
also merge into `.agent/memories/failures.json` by a deterministic fingerprint
of operation, kind, sanitized tool, failure mode, and optional exit code. The
bounded atomic artifact records only occurrence counts and Session IDs—never
errors, Prompt/source/review content, arguments, or output—so recurring failures
can guide later work without leaking the failed context.

Git-bound project changes use a separate digest-bound risk approval gate. The
Git integration prepares the exact path/kind set; the approval layer never
reads or stores source or diff content. Documentation, tests, and Session
evidence are low risk and record that approval is not required. Production
changes are medium risk, while deletions, dependency manifests, Agent control
files, and GitHub workflows are high risk. Medium/high changes remain pending
until an explicit human decision:

```bash
uv run agent approval status
uv run agent approval approve
uv run agent approval reject "Needs a migration plan"
```

The strict active-Session record binds the decision to the exact SHA-256 change
digest. Malformed, stale, symlinked, concurrently changed, or different
requests fail without replacing the existing decision.

After one implementation cycle reaches verified GREEN, optionally prepare and
commit only its current test and production artifacts:

```bash
uv run agent git prepare
uv run agent approval status
uv run agent approval approve
uv run agent git commit
```

Preparation runs a scoped, NUL-delimited Git status and creates the risk request
without touching the index. Commit reloads the GREEN artifact digests and Git
status, requires the same approved digest, stages only the two explicit paths,
verifies the cached names, revalidates again, and uses `git commit --only` with
the same paths. It never uses `git add .`; unrelated staged/worktree changes are
left out. Git stdout/stderr is not persisted or returned. The verified HEAD and
approval digest are returned, while the source-free approval record is archived
inside the Session for audit. This opt-in sequence can run after every GREEN
cycle before the next `agent continue` without changing legacy workflows.

Immediately after that scoped Agent commit, undo only the same current GREEN
cycle and return it to `WRITE_TEST` with:

```bash
uv run agent rollback
```

Rollback requires the active GREEN artifacts to be unchanged and clean, and
the single-parent Git HEAD subject/path set to match that exact Session and
test. It restores only the two validated paths from HEAD's parent with native
`git restore`, leaves HEAD and unrelated work unchanged, removes stale
current-cycle evidence, and lets the normal `agent continue` loop retry the
test. It cannot target arbitrary revisions, older cycles, or completed
Sessions; malformed, mismatched, dirty, or concurrently changed inputs fail
closed. If the atomic state update fails after file restoration, the same
paths are restored from HEAD before the error is returned.

The complete public-CLI sequence is covered by an isolated end-to-end
acceptance test using a fresh detected TypeScript/Vitest project. It verifies
every state transition, explicit human gate, Blind production context, exact
RED/current/full-suite command ordering, separate timeouts, audit records, and
the final DONE transition without invoking a real model, package manager, or
network service. Focused tests independently cover Java/JUnit, Angular CLI,
Jest, Vitest, Maven, Gradle, npm, pnpm, and yarn planning and recovery behavior.

The cross-ecosystem execution planner builds tokenized one-test and full-suite
commands for Maven or Gradle with JUnit 5, and for npm, pnpm, or yarn projects
using Jest, Vitest, or Angular CLI. Java uses fully qualified class/method
selectors. Node runners use one exact file plus an escaped and anchored
test-name expression; the suite plans contain no current-test filter. Vitest
and Angular watch behavior is disabled. Ambiguous lockfiles, conflicting
`packageManager` metadata, unverified frameworks, unsafe paths, and unsupported
layouts fail explicitly.

Inspect the exact implemented target ecosystem matrix without executing a build
or creating project metadata:

```bash
uv run agent ecosystem list
```

The documented scope is Java with Maven/Gradle/JUnit 5 and TypeScript with
npm/pnpm/Yarn plus Jest/Vitest/Angular. Other languages and frameworks are not
claimed until they have detection, command planning, TDD, and real-fixture
evidence.

For another provider, omit the protocol or set it to `json-command` and supply a
compatible JSON stdin/stdout command. Every command token must be a JSON string.

Inspect adapter-ready and planned Agent providers without executing them:

```bash
uv run agent provider list
uv run agent provider status
uv run agent provider doctor
uv run agent provider doctor codex
```

Select an implemented Provider explicitly:

```bash
uv run agent provider use codex
uv run agent provider use claude-code
uv run agent provider use cursor
```

When an adapter-ready CLI is missing in an interactive terminal, `provider use`
asks before downloading anything. The default is always No. Confirmation
downloads the current stable CLI from the Provider Registry's verified official
source, runs the installer as a separate tokenized process, re-locates the
executable, verifies `--version`, and only then updates project selection.
Decline or failure preserves configuration and Session state.

The Codex install plan follows the current
[official Codex CLI instructions](https://developers.openai.com/codex/cli/),
using `https://chatgpt.com/codex/install.sh`. The documented pipe is deliberately
split into a `curl --output` process and a separate `sh <temporary-script>`
process so this platform continues to use `shell=False`. No install is attempted
from non-interactive selection, and authentication remains a separate manual
step.

Codex, Claude Code, Cursor, and the custom JSON adapter are implemented. Claude
Code uses its documented print-mode JSON output with plan permissions and no
session persistence. Cursor uses print-mode JSON output without `--force`, so
the CLI boundary does not authorize direct project writes. Both normalize their
successful result envelope into the same strict typed JSON validators used by
every existing workflow. Their guarded install plans use the official
[Claude Code installer](https://code.claude.com/docs/en/installation) and
[Cursor CLI installer](https://docs.cursor.com/en/cli/installation).

GitHub Copilot remains planned until its JSONL programmatic event stream has a
dedicated bounded contract. Every workflow run continues to use exactly one
selected Provider.

External plugins and IDE clients can discover the versioned integration
contract without initializing or mutating a project:

```bash
uv run agent integration manifest
```

The plugin API is the existing explicit `json-command` external-process
boundary: typed JSON stdin/stdout, tracked finite-timeout configuration, and no
shell. The IDE API publishes stable read-only status, project-memory, and
Provider-status commands plus exit codes. Provider lifecycle data comes from
the Registry. Discovery never loads third-party Python code, starts a Provider,
uses the network, or changes environment/project state.

macOS and Linux Mint are target platforms. Every push and pull request now runs
the repository quality suite on explicit Ubuntu 24.04 workers with Python 3.9,
3.10, and 3.12. A separate compatibility job invokes the complete test suite
through both Bash and Zsh. This hosted coverage validates Linux portability; it
does not relabel Ubuntu as Linux Mint.

The separate **Toolchain fixtures** workflow executes real minimal projects on
Ubuntu rather than stopping at mocked process runners. Its matrix runs Maven
and Gradle with JUnit Jupiter, plus npm, pnpm, and Yarn with locked Vitest
TypeScript fixtures. The commands are the same full-suite commands produced by
the Agent's shell-free planners.

Real Linux Mint validation is deliberately separate and manual. Register a
self-hosted GitHub Actions runner with the labels `self-hosted`, `linux`, `x64`,
and `linuxmint`, then dispatch the **Linux Mint validation** workflow. The job
requires `agent platform doctor` to report the exact Linux Mint distribution,
the `supported-target` classification, and `ready` status before running all
quality gates. No host packages are installed by that workflow. Until a matching
runner completes it successfully, Linux Mint remains a supported target with
pending real-host CI evidence.

Inspect host identity and minimum runtime readiness without changing the project:

```bash
uv run agent platform doctor
```

On Linux, the Doctor follows the standard
[`os-release` contract](https://www.freedesktop.org/software/systemd/man/latest/os-release.html)
and recognizes only `ID=linuxmint` as the formally supported Linux Mint target.
Other Linux distributions report `compatible-untested`; they are not mislabeled
as Linux Mint. Python must be at least 3.9, and private temporary storage is
probed with automatic cleanup. macOS remains supported, while unsupported
systems and degraded runtime capabilities are reported explicitly.

Run the test suite with:

```bash
uv run python -m unittest discover -v
```

Repository quality checks are defined by `AGENTS.md` and can be run with:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```

The active and completed development records live under `.agent/sessions/`.
The multi-language delivery plan, including TypeScript and Angular SDD/TDD,
lives in `ROADMAP.md`.
