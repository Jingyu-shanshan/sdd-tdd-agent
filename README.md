# sdd-tdd-agent

A CLI platform for software-design-driven development (SDD) and incremental
test-driven development (TDD), built around a single agent with isolated
contexts.

## Current capabilities

The current slices provide a working CLI, project/session workspace,
requirement-analysis workflow, typed model adapters, and provider selection
while preserving the specification and incremental TDD record structure.

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
are reported without guessing a package manager or framework.

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

The writer permits only normalized supported source files below `src/` and
rejects test-like paths, configuration/build files, hidden paths, traversal,
symbolic links, stale targets, invalid UTF-8, and temporary collisions. Existing
source is replaced only if its captured content is unchanged; one safe new
source may be created. Success atomically records the production file ID, path,
and SHA-256 and advances only RED to IMPLEMENT:

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

Run the deterministic implementation audit after the exhausted plan enters
REVIEW:

```bash
uv run agent review
```

The command verifies the digest-bound completion snapshot against the retained
completed-test prefix, final test, GREEN evidence, and test/production artifact
records. It writes a bounded `review.md` containing IDs, counts, and digests—no
source or process output—then atomically enters REFACTOR. It invokes no model,
test runner, or shell command. The report explicitly marks semantic automated
code review as deferred to v0.3 instead of claiming uncomputed findings.

Finish the v0.1 workflow with deterministic refactor verification:

```bash
uv run agent refactor
```

This command implements the honest v0.1 refactor contract: it makes no source
change and invokes no model. It revalidates the complete review, completion,
GREEN-evidence, and final-source digest chain, reruns the recorded current test
and then the recorded unfiltered suite with separate timeouts, and requires two
zero exits. It stores only sanitized bounded final evidence and atomically
enters DONE. Any failed process, changed source or state, stale record, unsafe
path, or concurrent update preserves REFACTOR. Automated behavior-preserving
source refactoring remains planned for v0.3.

The cross-ecosystem execution planner builds tokenized one-test and full-suite
commands for Maven or Gradle with JUnit 5, and for npm, pnpm, or yarn projects
using Jest, Vitest, or Angular CLI. Java uses fully qualified class/method
selectors. Node runners use one exact file plus an escaped and anchored
test-name expression; the suite plans contain no current-test filter. Vitest
and Angular watch behavior is disabled. Ambiguous lockfiles, conflicting
`packageManager` metadata, unverified frameworks, unsafe paths, and unsupported
layouts fail explicitly.

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

Codex and the custom JSON adapter are implemented. Claude Code, Cursor, and
GitHub Copilot are listed as planned and cannot be selected until their current
CLI, structured-output, authentication, and licensing contracts have dedicated
Adapters and contract tests. Every workflow run continues to use exactly one
selected Provider.

macOS and Linux Mint are target platforms. Linux Mint support will be validated
through a formal Python, shell, subprocess, permission, timeout, Java, and
TypeScript toolchain matrix described in `ROADMAP.md`; the CLI will not silently
install provider tools or mutate PATH.

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
