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
also record JUnit 5 as their test framework.

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
errors. CLI orchestration for task breakdown is deferred to the next increment.

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
