# Test plan

1. Request loading: raw feature request, context files, Prompt version/content.
2. Rendering: all structured sections, list values, original request, and empty
   optional list representation.
3. Workflow: fake analyzer receives typed request; requirement and state update.
4. Validation: invalid output and wrong state fail before mutation.
5. Packaging: built wheel contains Prompt v1.
6. Regression: all existing feature, status, detection, init, and CLI tests.

