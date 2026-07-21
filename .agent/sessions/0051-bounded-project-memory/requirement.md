# Requirement

## Goal

Formalize the existing tracked project metadata, architecture, and conventions
as bounded project memory shared across Sessions and consumed through one safe
typed loader.

## Acceptance criteria

- Project memory remains the three existing tracked files; no duplicate store.
- Loading rejects missing, empty, symlinked, non-UTF-8, oversized, or
  concurrently changed memory.
- One deterministic digest identifies the exact three-file snapshot.
- Requirement analysis uses the shared validated snapshot.
- `agent memory` reports readiness, digest, and bounded sizes without exposing
  content.
- Project initialization and all existing workflows remain compatible.

## Out of scope

- Model-written memory, vector databases, embeddings, or semantic retrieval.
- Storing source, Prompt, credentials, or personal data in runtime memory.
- Automatic modification of human-maintained architecture or conventions.
