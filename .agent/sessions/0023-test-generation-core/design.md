# Design

## Typed model

- `TestGenerationRequest`: versioned Prompt, approved requirement/design/tasks,
  and tracked project context.
- `TestCasePlan`: one ordered test specification with stable IDs, phase,
  execution description, expected outcomes, target, and prior dependencies.
- `GeneratedTestPlan`: summary, ordered cases, risks, and open questions.
- `TestPlanGenerator`: injected Protocol with one `generate(request)` call.
- `TestGenerationRun`: completed Session transition and validated plan.

## Incremental ordering

The supported phase order is `happy_path`, `boundary`, `exception`,
`integration`, then `regression`. The first case must be happy path and phase
rank may never decrease. Stable test IDs are unique; dependencies may reference
only already validated IDs, preventing unknown, forward, self, and cyclic
dependencies. Every task ID parsed from generated task headings must be covered.

## Safety

Target test files must be non-empty relative paths. Absolute POSIX/Windows paths,
NUL values, and `..` traversal are rejected. Required scalar/list content is
validated before output. The plan contains descriptions, never executable test
or production code.

## State transition

```text
TASK_REVIEW --human approve--> TEST_GENERATION
TEST_GENERATION --valid plan--> IMPLEMENTATION
```

## Output

`test-plan.md` renders summary, ordered cases, phase/task/target, preconditions,
action, expected outcomes, dependencies, risks, and questions. Optional empty
lists render explicitly. Artifact and state use Session-local atomic writes.
