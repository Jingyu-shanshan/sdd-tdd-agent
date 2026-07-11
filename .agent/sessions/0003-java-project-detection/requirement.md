# Requirement: Detect Java build tools

## Description

Enhance initialization of a new agent workspace with lightweight Java project
detection based on conventional build-tool marker files.

## User story

As a Java developer initializing the platform, I want the generated project
metadata to record my build tool so later test and compile commands can be
selected correctly.

## Functional requirements

- A root-level `pom.xml` identifies a Java Maven project.
- A root-level `build.gradle` identifies a Java Gradle project.
- A root-level `build.gradle.kts` identifies a Java Gradle project.
- A fresh `agent init` persists `target_language: java` and the detected
  `build_tool` in `.agent/project.yml`.
- A project with none of these markers remains unclassified.

## Non-functional requirements

- Detection reads filenames only; it does not execute project code or builds.
- Detection is independent of workspace creation and can be unit tested.
- Existing `.agent/project.yml` files remain protected by init's first-write
  policy.
- No runtime third-party dependency is introduced.

## Deferred scope

- Projects containing conflicting Maven and Gradle markers.
- Multi-module and nested build discovery.
- Wrapper detection and build-tool version detection.
- JUnit, Mockito, Testcontainers, Checkstyle, SpotBugs, and PMD detection.
- Parsing XML, Groovy, or Kotlin build definitions.

