# Design: Hello World CLI

## Components

- `sdd_tdd_agent.cli`: parses CLI arguments and dispatches commands.
- `sdd_tdd_agent.__main__`: module execution adapter.
- `hello(out)`: command behavior that writes to an injected text stream.

## Data flow

```text
argv -> main -> hello -> stdout -> process exit 0
```

## Interface

```text
agent hello
python -m sdd_tdd_agent hello
```

## Risks and controls

- CLI frameworks can obscure exit behavior during bootstrap; use `argparse`.
- Direct printing is awkward to test; inject the output stream into `hello`.
- Future commands may outgrow a single module; defer abstraction until a test
  demonstrates the need.

