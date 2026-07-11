# Test plan

1. Happy path: explicit safe ID creates the exact artifact set and state.
2. Metadata integration: existing and missing `current_session` cases preserve
   all unrelated lines.
3. CLI boundary: generated ID is reported and points to the created Session.
4. Validation: blank request and unsafe explicit ID fail before mutation.
5. Regression: all existing initialization, detection, status, and CLI tests.

