# Design: Create a feature session

## Components

- `FeatureSession`: immutable result containing the ID and path.
- `create_feature_session(root, description, session_id=None)`: validates input,
  creates artifacts, and activates the session.
- Private ID generation uses UTC time plus a sanitized description slug.
- Private project-metadata update replaces only a root-level
  `current_session` scalar or appends it when absent.
- CLI dispatch joins the feature arguments as the user request and reports the
  returned ID.

## Data flow

```text
feature text -> validate -> safe session ID -> exclusive session directory
             -> pending SDD artifacts + ANALYSIS state
             -> project.yml current_session -> CLI confirmation
```

## Artifact policy

Only the user request is known at creation time. Downstream artifacts contain a
clear pending marker. Future workflow states will populate them after their own
tests and approval rules exist.

## Security and recovery

- Description must contain non-whitespace text.
- Session IDs are restricted to one safe path segment.
- Directory creation fails if the ID already exists.
- Project metadata is rewritten through a sibling temporary file and atomically
  replaced after the new Session is complete.

