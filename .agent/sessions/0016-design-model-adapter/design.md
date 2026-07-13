# Design

## Module boundary

`design_adapter` depends on the stable process/configuration/resolver contracts
in `model_adapter` and on typed design request/result models in
`design_generation`. This keeps requirement-specific decoding out of the design
domain without duplicating subprocess execution.

## JSON command adapter

`JsonCommandDesignGenerator` serializes the six request fields with Unicode
preserved, invokes the configured tokenized command once, checks its exit code,
strictly decodes the response, and returns `DesignProposal`.

## Codex exec adapter

`CodexExecDesignGenerator` requires exactly one configured executable and uses:

```text
codex exec --ephemeral --sandbox read-only --color never
  --output-schema <temporary-schema>
  --output-last-message <temporary-result>
  --cd <project-root> -
```

The schema requires all ten design fields, permits no additional properties,
and restricts collection items to strings. A private automatically cleaned
temporary directory holds the schema and output.

## Error policy

- Nonzero commands expose only the numeric exit code.
- Invalid JSON, object shape, exact keys, scalar types, and array item types
  have stable category messages.
- Missing/unreadable Codex output maps to one safe error.
- Request and process content never appear in public errors.
- Domain-level non-empty validation remains in `run_design_generation`.
