# Design

## Components

- `DesignGenerationRequest`: versioned Prompt plus approved requirement and
  tracked project context.
- `DesignProposal`: immutable structured generator output.
- `DesignGenerator`: injected Protocol with one `generate(request)` operation.
- Request loader: validates the Session identifier and loads only tracked
  inputs.
- Renderer: emits stable Markdown sections and explicit empty optional sections.
- Workflow: validates state and approval, invokes the generator, validates all
  output, atomically writes design/state, and returns a typed result.

## State transition

```text
REQUIREMENT_REVIEW --human approve--> DESIGN
DESIGN --valid generated proposal----> DESIGN_REVIEW
```

Generation requires both `state == DESIGN` and the persisted
`requirement_review.decision == approved` record. It never advances directly to
task breakdown.

## Validation

- Session identifiers use the existing safe generated identifier contract.
- State must be a JSON object and identify the requested Session.
- Requirement Markdown must be a non-empty analyzed requirement.
- Overview, architecture decisions, components, data flow, and testing strategy
  are required.
- Every tuple item must be a non-empty string; optional sections may be empty.
- The generator must return the exact typed proposal class.

## Failure policy

All context, state, approval, generator type, and proposal validation happens
before design/state replacement. Invalid input or output propagates as an
explicit error and leaves the existing artifact and state unchanged.
