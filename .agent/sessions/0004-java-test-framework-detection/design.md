# Design: Detect JUnit 5 in Maven projects

## Components

- Extend `ProjectProfile` with an immutable tuple of test-framework names.
- Add private Maven dependency inspection in `project_detection`.
- Extend `project_init` metadata rendering for non-empty framework tuples.

## Recognition rule

Within a Maven `<dependency>` element:

```text
groupId == org.junit.jupiter
artifactId starts with junit-jupiter
```

Both elements must belong to the same dependency. Namespace handling will
compare XML local names rather than hardcode a Maven namespace version.

## Data flow

```text
pom.xml -> XML dependency inspection -> ProjectProfile.test_frameworks
        -> first-write YAML rendering -> project.yml
```

## Error policy

This increment parses valid local POM files. `ElementTree.ParseError` is not
suppressed; invalid XML fails explicitly rather than silently producing false
metadata. A user-facing domain error is deferred until CLI error handling is
specified.

