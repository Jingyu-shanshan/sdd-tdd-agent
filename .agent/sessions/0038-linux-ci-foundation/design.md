# Design

## Hosted Linux workflow

Create `.github/workflows/ci.yml` with read-only repository permissions and
automatic push and pull-request triggers. A quality job uses the explicit
`ubuntu-24.04` image and a Python 3.9, 3.10, and 3.12 matrix. Each matrix entry
syncs the locked development environment and runs all repository quality gates;
Python 3.12 also proves that the distribution builds.

A separate shell-compatibility job installs Zsh only on the disposable hosted
Ubuntu worker and runs the full pytest contract through both Bash and Zsh.

## Linux Mint workflow

Create `.github/workflows/linux-mint.yml` with only a manual
`workflow_dispatch` trigger. It requires all four self-hosted labels:
`self-hosted`, `linux`, `x64`, and `linuxmint`. This prevents ordinary pushes
from indefinitely queuing when no Mint runner is registered and prevents a
generic Linux runner from being mistaken for Mint.

Before the quality gates, `agent platform doctor` output must state the exact
Linux Mint distribution, supported-target classification, and ready runtime.
The workflow does not install or mutate host packages.

## Supply-chain boundary

External Actions are fixed to audited full commit SHAs with readable release
comments. Workflow permissions expose only read access to repository contents.
No secrets or write permissions are required.

## Validation strategy

Python tests treat both workflow files as versioned declarative contracts. This
avoids a new YAML dependency while checking triggers, runners, matrices, action
pins, commands, and Linux Mint safeguards. Repository gates then validate the
test and documentation changes.
