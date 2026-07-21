# Design

Extract the filesystem mechanics currently embedded in `feature_session.py`
into a small internal `session_creation.py` service. It owns input/ID validation,
slug generation, standard artifact rendering, exclusive Session directory
creation, and atomic active-session metadata replacement.

`feature_session.py` retains its existing typed result and public function while
delegating to the shared service. A parallel `bug_session.py` exposes a typed
`BugSession` and delegates with `kind=bug`. The CLI maps only exact first-token
`bug` requests to the new service and emits deterministic output.

No downstream workflow needs a bug branch: existing state services operate on
the active Session and preserve the `kind` field.
