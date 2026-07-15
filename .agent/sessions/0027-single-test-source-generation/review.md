# Review

The change keeps Test Context structurally separate from Blind Development
Context. Source paths cannot traverse, access `.agent`/`.git`, duplicate, carry
null bytes, or exceed the size limit. Provider responses cannot redirect output
to another test or file, and public command errors contain no request, output,
stderr, or temporary path content. The model exchange is read-only and does not
mutate Session or project files.

No dependency, public CLI, unrelated refactor, secret, or `.gitignore` change
was introduced.
