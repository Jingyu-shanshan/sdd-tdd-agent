# Design

## Domain model

`ProviderDefinition` records a stable key, display name, lifecycle status,
supported platforms, and optional implemented protocol/command. Only definitions
with `adapter-ready` status and complete adapter configuration are selectable.

`ProviderSelection` represents the provider inferred from strict analyzer
configuration without executing it.

## Application operations

- `list_providers()` returns the immutable registry.
- `load_provider_selection(root)` maps current analyzer configuration to a
  registered provider or the provider-neutral `custom-json` selection.
- `select_provider(root, key)` validates availability, preserves the explicit
  timeout and unrelated keys, and atomically updates only protocol/command.
- Render functions produce deterministic CLI text independently of dispatch.

## CLI

```text
agent provider list
agent provider status
agent provider use <key>
```

Invalid usage and selection errors return exit code 2 on stderr. Provider
operations never run a model or mutate Session state.

## Extensibility

Future adapters add a registry definition only after their protocol
implementation passes the shared analyzer contract suite. Registry membership
does not imply that an executable is installed; `provider doctor` will cover
runtime diagnostics in a later increment.
