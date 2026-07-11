# Design: Detect Java build tools

## Components

- `sdd_tdd_agent.project_detection.ProjectProfile` represents detected
  language and build tool.
- `detect_project(root)` performs side-effect-free marker inspection.
- `initialize_project(root)` uses the profile only while creating a new
  `project.yml`.

## Detection rules

```text
pom.xml          -> java / maven
build.gradle     -> java / gradle
build.gradle.kts -> java / gradle
no marker        -> no profile
```

Conflict precedence is intentionally undefined until a failing test specifies
the desired behavior.

## Data flow

```text
project root -> marker inspection -> optional ProjectProfile
             -> init metadata rendering -> .agent/project.yml
```

## Risks and controls

- False positives from nested files: inspect root-level paths only.
- Side effects during detection: use filesystem existence checks only.
- Existing metadata loss: retain exclusive first-write initialization.

