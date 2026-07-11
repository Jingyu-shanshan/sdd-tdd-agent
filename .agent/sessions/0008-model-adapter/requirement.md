# Requirement: JSON command model adapter

## Description

Implement a provider-neutral adapter that invokes an explicitly configured
executable using a strict JSON stdin/stdout protocol and returns typed
requirement analysis.

## User story

As a platform integrator, I want a safe command adapter boundary so Claude,
Codex, Gemini, Ollama, or a custom bridge can perform requirement analysis
without coupling the core workflow to a provider SDK.

## Functional requirements

- Serialize every `RequirementAnalysisRequest` field to one JSON object.
- Invoke a configured command as an argument tuple with `shell=False`.
- Send JSON through stdin and capture stdout/stderr separately.
- Apply an explicitly supplied positive timeout.
- Accept only a JSON object containing the six required analysis fields.
- Accept `summary` as a string and the five collection fields as arrays of
  strings.
- Convert valid output into immutable `RequirementAnalysis`.
- Convert non-zero exit, timeout, invalid JSON, missing/extra keys, and invalid
  field types into a dedicated adapter error.
- Never include captured stdout/stderr, Prompt text, or project context in error
  messages.

## Non-functional requirements

- Process execution is behind a typed, mockable `ProcessRunner` Protocol.
- The production runner uses standard-library `subprocess` only.
- No shell interpolation, global mutation, environment mutation, SDK, or
  credential handling is introduced.
- Command and timeout configuration are immutable and validated.
- All public functions/classes are typed and all `AGENTS.md` gates pass.

## Deferred scope

- `.agent/config.yml` adapter configuration.
- `agent analyze` CLI integration.
- Provider-specific command construction or authentication.
- Streaming, retries, token/cost metrics, cancellation, and schema negotiation.

