# Design

## Platform environment

`PlatformEnvironment` supplies four read-only operations:

- operating-system identifier;
- Python version tuple;
- optional Linux `os-release` content;
- private temporary-directory probe result.

`SystemPlatformEnvironment` implements these with `sys.platform`,
`sys.version_info`, `/etc/os-release` then `/usr/lib/os-release`, and an
automatically cleaned `TemporaryDirectory`.

## os-release parser

The parser follows the freedesktop/systemd `os-release` key/value contract. It
accepts unquoted or shell-style quoted scalar values without expansion, ignores
comments/blank lines, and rejects invalid assignments, duplicate keys, control
characters, or multi-token values. Only `ID` and `VERSION_ID` are retained.

## Classification

- `darwin` -> `macos`, platform support `supported`.
- `linux` + `ID=linuxmint` -> support `supported-target`.
- other/missing Linux ID -> support `compatible-untested`.
- other systems -> support `unsupported`.

Python status and temporary-directory status remain separate. Readiness is
`ready` only when the platform is supported, Python is >=3.9, and temporary
storage works; compatible untested Linux reports `review-required`; missing
runtime capabilities report `degraded`.

## CLI

`agent platform doctor` constructs the system environment, diagnoses it, and
renders deterministic text. It does not require or mutate `.agent` state.
