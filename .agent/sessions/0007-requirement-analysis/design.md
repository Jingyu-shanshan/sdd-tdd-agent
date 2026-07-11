# Design: Analyze a feature request

## Components

- `RequirementAnalysisRequest`: typed Prompt, version, raw request, and project
  context.
- `RequirementAnalysis`: typed structured analyzer output.
- `RequirementAnalyzer`: Protocol with one mockable `analyze(request)` method.
- Request loader: reads only the selected Session and tracked project context.
- Renderer: deterministic Markdown with stable section ordering.
- Workflow: validates state/output, invokes the injected analyzer, atomically
  replaces requirement/state files, and returns a typed result.

## Data flow

```text
requirement.md + architecture + conventions + project.yml + prompt/v1.md
                              -> RequirementAnalysisRequest
                              -> injected RequirementAnalyzer
                              -> RequirementAnalysis validation
                              -> structured requirement.md
                              -> state REQUIREMENT_REVIEW
```

## Human-in-the-loop rule

All generated requirement analysis stops at `REQUIREMENT_REVIEW`, whether or
not the analyzer returned open questions. A later explicit approval workflow is
required to enter DESIGN.

## Failure policy

- Missing context, invalid source template, invalid JSON, wrong state, analyzer
  failure, or empty required output propagates as an explicit error.
- Analyzer output is validated before any Session file is replaced.
- The requirement file is replaced before state; a state-write failure leaves
  the workflow observable for recovery rather than falsely claiming success.

