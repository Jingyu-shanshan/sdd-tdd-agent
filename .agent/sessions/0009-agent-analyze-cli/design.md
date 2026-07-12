# Design: Run requirement analysis from the CLI

## Components

- `AnalyzerConfigurationError`: safe configuration failure.
- `load_analyzer_config(root)`: strict command-list and timeout parser.
- `analyze_active_requirement(root, runner)`: composition service that resolves
  the active Session, constructs the adapter, and runs analysis.
- CLI `analyze` dispatch: injects a supplied runner or creates
  `SubprocessRunner`, renders one deterministic success line, and returns 0.

## Data flow

```text
config.yml -> CommandAnalyzerConfig ------+
project.yml -> current_session -----------+-> JSON adapter
injected/default ProcessRunner -----------+-> requirement workflow
                                             -> REQUIREMENT_REVIEW -> stdout
```

## Parsing rules

- Command begins at exact root key `requirement_analyzer_command:`.
- Each indented item must begin `- ` and contain one JSON string.
- Timeout is an exact root scalar parsed as a finite positive float.
- Duplicate command/timeout declarations, empty lists, and invalid items fail.
- Unknown keys remain ignored so existing loop-control configuration works.

## Safety

- Parsed command items remain separate arguments.
- No shell splitting or interpolation occurs.
- Configuration errors expose key/category only, never configured values.
- Workflow validates ANALYSIS state before the runner is called.

