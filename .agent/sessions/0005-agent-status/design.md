# Design: Show project and session status

## Components

- `ProjectStatus`: immutable typed snapshot for display fields.
- `load_project_status(root)`: reads platform-generated YAML and session JSON.
- `render_project_status(status)`: produces deterministic plain text.
- CLI dispatch supplies the project root and output stream.

## Data flow

```text
.agent/project.yml -----> scalar/list reader ----+
                                                +-> ProjectStatus -> renderer
session/state.json -----> JSON state reader -----+                  -> stdout
```

## Parsing boundary

The reader supports only the flat scalar keys and indented string lists emitted
by `project_init`. It does not claim to be a general YAML parser. Introducing a
YAML dependency requires a separate need, design, and approval.

## Defaults

Missing optional display fields are represented as `unknown` for project
classification and `none` for lists or session state. Missing workspace policy
is deferred so this increment can stay on the initialized-project happy path.

## Security boundary

`current_session` is validated as one path segment before it is joined to the
sessions directory. Slash, backslash, `.` and `..` identifiers are rejected.
