# Design

## Configuration

Add an optional root scalar:

```yaml
requirement_analyzer_protocol: codex-exec
```

`json-command` remains the backward-compatible default. The existing command
list supplies the Codex executable, and the existing explicit timeout is reused
for the single Codex process.

## Adapter

`CodexExecRequirementAnalyzer` implements the existing typed analyzer Protocol.
It creates a private temporary exchange directory, writes the strict response
JSON Schema, and invokes the injected `ProcessRunner` with:

```text
codex exec --ephemeral --sandbox read-only --color never
  --output-schema <temporary-schema>
  --output-last-message <temporary-result>
  --cd <project-root> -
```

The analysis request JSON is supplied through stdin. On success, the adapter
reads only the temporary result file and reuses the existing strict decoder.
Temporary exchange files live outside the repository and are removed
automatically.

## Safety

- `shell=False` remains enforced by `SubprocessRunner`.
- The configured Codex command must contain exactly one executable token.
- No model, credential, or user-global Codex configuration is overridden.
- Errors expose only stable categories and exit codes.
- Session files mutate only after the existing domain validator accepts output.
