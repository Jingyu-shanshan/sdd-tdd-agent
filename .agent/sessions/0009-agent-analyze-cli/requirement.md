# Requirement: Run requirement analysis from the CLI

## Description

Connect project configuration, the active feature Session, the JSON command
adapter, and requirement-analysis workflow behind `agent analyze`.

## User story

As a developer with an ANALYSIS feature Session and configured model bridge, I
want `agent analyze` to generate structured requirements and stop for review.

## Configuration format

`.agent/config.yml` uses this restricted tracked subset:

```yaml
requirement_analyzer_command:
  - "model-bridge"
  - "analyze"
requirement_analyzer_timeout_seconds: 45
```

Each command item is a JSON string. This preserves spaces/escaping while
keeping execution tokenized and shell-free. Timeout is required and has no
implicit default.

## Functional requirements

- Load command and timeout from `.agent/config.yml`.
- Preserve unrelated existing configuration keys.
- Reject missing, duplicate, malformed, empty, or invalid analyzer settings.
- Resolve the active Session from `.agent/project.yml`.
- Reject a project without an active Session.
- Compose `JsonCommandRequirementAnalyzer`, injected/default runner, and
  `run_requirement_analysis`.
- `agent analyze` writes the completed Session ID and
  `REQUIREMENT_REVIEW` state, then exits 0.
- Fail before analyzer execution when configuration, active Session, or Session
  state is invalid.

## Non-functional requirements

- Configuration parsing supports only the documented subset and does not claim
  general YAML support.
- Runner injection remains available from the CLI composition boundary.
- Do not include command values, process content, Prompt, or project context in
  configuration or execution errors.
- Do not store API keys, tokens, credentials, or database URLs in config.
- No new runtime dependency is introduced.
- All `AGENTS.md` quality gates pass.

## Deferred scope

- Provider-specific bridge installation and authentication.
- Multiple named adapters and per-stage model selection.
- CLI flags overriding tracked configuration.
- Streaming, progress UI, retries, logs, token/cost metrics, and cancellation.
- Human approval command after REQUIREMENT_REVIEW.

