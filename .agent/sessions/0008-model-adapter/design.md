# Design: JSON command model adapter

## Types

- `CommandAnalyzerConfig`: immutable command tuple and timeout.
- `ProcessResult`: immutable exit code, stdout, and stderr.
- `ProcessRunner`: typed `run(command, stdin, timeout)` tool boundary.
- `SubprocessRunner`: production shell-free implementation.
- `JsonCommandRequirementAnalyzer`: request serialization and strict response
  decoding.
- `RequirementAnalyzerError`: public safe adapter failure.

## Wire protocol

Input JSON keys:

```text
prompt_version, prompt, user_request,
project_metadata, architecture, conventions
```

Output JSON keys:

```text
summary, user_stories, functional_requirements,
non_functional_requirements, impact_analysis, open_questions
```

No additional keys are accepted in v1. Collections are JSON arrays of strings.

## Security

- The command is already-tokenized configuration; no shell is started.
- No environment variables are created or modified.
- Errors expose only category and exit code, never process output or request
  content.
- Schema validation happens before domain object construction.

