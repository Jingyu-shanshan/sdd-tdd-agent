# Requirement

## Goal

Publish a versioned machine-readable integration contract that exposes the
existing external JSON Provider protocol as the plugin API and stable read-only
CLI entry points for IDE clients.

## Acceptance criteria

- `agent integration manifest` emits deterministic strict JSON.
- The manifest versions the contract and lists every supported model operation.
- Plugin execution remains the existing explicit shell-free `json-command`
  boundary with typed JSON stdin/stdout and finite timeout configuration.
- IDE clients discover stable status, project-memory, and Provider commands plus
  success/error exit codes.
- Provider capabilities are derived from the Registry, including lifecycle
  status and protocol.
- Manifest discovery performs no project mutation, provider execution, plugin
  loading, network access, or environment mutation.

## Out of scope

- In-process dynamic code loading or automatic plugin discovery/execution.
- Shipping editor-specific VS Code, IntelliJ, or language-server extensions.
- A background daemon, socket protocol, or additional dependency.
