# Implementation

## Cycle 1: Fixture and workflow contracts

Status: RED complete.

Tests require real planner-readable fixtures and an immutable five-toolchain
workflow before any fixture or workflow implementation is present.

All eight focused cases failed for the intended reason: the five fixture roots
and toolchain workflow did not exist.

## Cycle 2: Real fixtures

Status: GREEN complete.

Maven and Gradle fixtures contain one Java behavior and JUnit Jupiter 6.1.2
test. npm, pnpm, and Yarn fixtures contain the same TypeScript behavior and real
Vitest test. Manager-specific lockfiles were generated from verified npm source
metadata.

The first lock generation exposed critical advisory GHSA-5xrq-8626-4rwp in
Vitest 4.0.0. The direct dependency was updated to fixed stable version 4.1.10,
all locks were regenerated, and npm now reports zero vulnerabilities. No forced
or broad dependency rewrite was used.

## Cycle 3: Toolchain workflow

Status: GREEN complete.

The automatic Ubuntu workflow defines two Java and three Node jobs. External
Actions, Java 21, Gradle 9.6.1, Node 22, and all package managers are explicit.
Node installs are immutable or frozen and every test command matches the
production full-suite planner.

All eight focused contracts pass. npm, pnpm, and Yarn also install and execute
their real tests locally. Maven and Gradle remain remote-only evidence because
the development host lacks usable installations.

## Cycle 4: Verification

Status: complete pending the push-triggered confirmation recorded at handoff.

All 673 pytest cases pass with 93.78% coverage. Ruff lint and formatting,
Pyright, workflow YAML, Maven XML, pnpm YAML, Agent and fixture JSON, production
compilation, package build, secret scanning, and active-Session preservation all
pass.

npm and Yarn report no advisories. The pinned pnpm 10 audit client and the
latest pnpm 10 client both receive HTTP 410 from npm's retired legacy audit
endpoint; this is recorded rather than misreported as a successful pnpm audit.
The original critical direct Vitest advisory is removed from every lock at
4.1.10, and npm's equivalent graph audit reports zero vulnerabilities.

The `.gitignore` audit found that Node `node_modules`, Yarn linker state, PnP,
and unplugged/build-state outputs needed repository rules. Those localized rules
were added; all installed fixture artifacts are now ignored while package
metadata, sources, and lockfiles remain tracked.
