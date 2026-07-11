# Requirement: Detect JUnit 5 in Maven projects

## Description

Extend Java Maven project detection so a fresh agent workspace records JUnit 5
when the root `pom.xml` declares a JUnit Jupiter dependency.

## User story

As a Java developer using Maven and JUnit 5, I want `agent init` to record my
test framework so later TDD commands can select the correct test conventions.

## Functional requirements

- A dependency whose group is `org.junit.jupiter` and whose artifact starts
  with `junit-jupiter` identifies JUnit 5.
- Detection works for POM files with no XML namespace.
- Detection works for the standard Maven XML namespace.
- The detected profile exposes `junit5` as a test framework.
- Fresh initialization writes the framework to `.agent/project.yml` as:

  ```yaml
  test_frameworks:
    - junit5
  ```

- A Maven project without a matching dependency has no detected test
  frameworks.

## Non-functional requirements

- Use Python's standard XML library; add no runtime dependency.
- Do not execute Maven or project code.
- Keep the profile immutable and typed.
- Preserve existing `.agent/project.yml` files.
- All quality gates from `AGENTS.md` must pass.

## Deferred scope

- Malformed or adversarial XML policy.
- Maven parent-POM and imported dependency resolution.
- Gradle dependency parsing.
- JUnit 4, TestNG, Mockito, and Testcontainers.
- Test framework versions and Maven profiles.

