# Design

## Typed model

- `TaskBreakdownRequest`: versioned Prompt, approved requirement/design, and
  tracked project context.
- `DevelopmentTask`: stable ID, title, objective, affected areas, dependencies,
  acceptance criteria, and test targets.
- `TaskBreakdown`: summary, ordered task tuple, global risks, and open questions.
- `TaskBreakdownGenerator`: injected Protocol with one `generate(request)` call.
- `TaskBreakdownRun`: completed Session transition and validated breakdown.

## Dependency contract

Task tuple order is execution order. IDs must match a safe alphanumeric
identifier contract and be unique. Every dependency must be a non-empty string
that appears in the already-validated ID set. This rejects unknown dependencies,
forward references, self-dependencies, and cycles without a separate graph
algorithm.

## State transition

```text
DESIGN_REVIEW --human approve--> TASK_BREAKDOWN
TASK_BREAKDOWN --valid tasks----> TASK_REVIEW
```

Generation requires both stored requirement and design approvals. It never
enters test generation directly.

## Output and failure policy

`tasks.md` renders the summary, each task in order with explicit list sections,
then global risks and open questions. Empty optional lists render `None
identified`. All state/context/type/content/dependency validation occurs before
the task artifact or Session state is replaced.
