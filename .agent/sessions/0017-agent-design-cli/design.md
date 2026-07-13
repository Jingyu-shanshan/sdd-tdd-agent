# Design

## Composition service

`design_command.generate_active_design` performs only orchestration:

```text
project.yml -> active Session ---------+
config.yml  -> protocol/command/timeout+-> design adapter
injected runner/resolver --------------+-> design workflow
                                          -> DESIGN_REVIEW
```

The service reuses `load_analyzer_config` because Provider selection currently
persists the single active model protocol, executable command, and timeout in
those tracked keys. `codex-exec` constructs `CodexExecDesignGenerator`; the
provider-neutral default constructs `JsonCommandDesignGenerator`.

## CLI

`agent design` injects the supplied runner or creates `SubprocessRunner`, calls
the composition service, and renders exactly:

```text
Design ready for review: <session-id> (DESIGN_REVIEW)
```

The CLI catches validated configuration/workflow/model adapter errors, writes a
single sanitized stderr line, and returns exit code 2.

## Safety

- Active Session resolution happens before configuration or process execution.
- The design workflow independently enforces DESIGN state and human approval.
- No command is shell-split or interpolated.
- No model, credential, environment, or user configuration is overridden.
