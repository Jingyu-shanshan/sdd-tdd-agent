# Implementation

## Cycle 1: CI contract

Status: RED complete.

The contract first requires explicit hosted Linux coverage and a separate,
manual real-host Linux Mint workflow. Production workflow files are intentionally
absent until the focused tests demonstrate the missing behavior. All three
focused tests failed because the workflow files did not exist.

## Cycle 2: Hosted Linux

Status: GREEN complete.

The automatic workflow uses Ubuntu 24.04 with Python 3.9, 3.10, and 3.12. It
runs locked dependency synchronization, Ruff lint and format validation,
Pyright, coverage-enforced pytest, and a Python 3.12 distribution build. A
separate matrix runs pytest through Bash and explicitly installed Zsh.

## Cycle 3: Linux Mint

Status: GREEN complete; real-host execution pending.

The Linux Mint workflow is manual-only and requires a self-hosted Linux x64
runner carrying the custom `linuxmint` label. Platform Doctor evidence prevents
a generic Linux runner from satisfying the job. The self-hosted workflow does
not install packages and disables persistent uv caching.

## Cycle 4: Verification

Status: complete.

The focused workflow contracts pass. Ruff lint and format checks, Pyright, and
all 664 pytest cases pass with 93.78% total coverage. The source distribution
and wheel build successfully, production modules compile, both workflow files
parse as YAML, all Agent JSON parses, no secret-shaped values are found, and the
active user Session is unchanged.

The `.gitignore` audit found only expected generated Python caches, coverage,
virtual-environment, egg-info, build, and distribution paths. Existing rules
already cover every generated artifact, so no ignore rule was added.
