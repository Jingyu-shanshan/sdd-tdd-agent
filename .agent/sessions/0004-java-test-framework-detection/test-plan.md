# Test plan

1. Happy path: non-namespaced POM with `junit-jupiter` dependency.
2. Compatibility: standard Maven namespace with `junit-jupiter-api`.
3. Integration: initialize a matching Maven project and inspect YAML.
4. Negative: Maven dependency not belonging to JUnit Jupiter.
5. Regression: run all existing CLI, initialization, and project-detection
   tests unchanged except for the explicitly approved Pyright narrowing fix.

