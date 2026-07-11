# Requirement: Analyze a feature request

## Description

Implement the ANALYSIS workflow boundary that sends a typed request to an
injected requirement analyzer, records structured results, and stops for human
review before design begins.

## User story

As a developer with an active feature Session, I want the raw request analyzed
into explicit stories, requirements, impacts, and questions so I can review the
scope before software design starts.

## Functional requirements

- Load the exact user request from the feature Session's `requirement.md`.
- Load project metadata, architecture, and conventions as analysis context.
- Load a versioned requirement-analysis Prompt from a tracked file.
- Provide all analyzer input through an immutable typed request.
- Accept analyzer output through an immutable typed result containing summary,
  user stories, functional requirements, non-functional requirements, impact
  analysis, and open questions.
- Render the structured result into `requirement.md` while retaining the
  original request and Prompt version.
- Update `state.json` from `ANALYSIS` to `REQUIREMENT_REVIEW` only after valid
  analysis output is written.
- Reject invalid output and invalid workflow state before mutation.

## Non-functional requirements

- The analyzer is injected through a typed Protocol and is mockable in tests.
- No model SDK or runtime dependency is introduced in this increment.
- Prompt text is versioned, stored outside business logic, packaged with the
  Python distribution, and tracked by Git.
- File updates use same-directory temporary files and atomic replacement.
- AI output is never allowed to silently advance into DESIGN; human review is
  mandatory.
- All `AGENTS.md` quality gates pass.

## Deferred scope

- Concrete Claude, Codex, OpenAI, Gemini, or Ollama adapters.
- `agent analyze` configuration and model selection.
- Human approve/reject/edit commands.
- Token, cost, duration, retry, and Prompt logging.
- Automatic movement from `REQUIREMENT_REVIEW` to `DESIGN`.

